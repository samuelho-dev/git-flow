#!/usr/bin/env python3
"""Run with python3 -m unittest discover -s tests -p 'test_garage_artifact.py'."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / '.github/actions/garage-artifact/artifact.py'
spec = importlib.util.spec_from_file_location('garage_artifact', SCRIPT)
artifact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(artifact)


class ArtifactTest(unittest.TestCase):
    def test_globs_preserve_relative_paths_and_exclude_hidden(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in ('apps/desktop/release/linux/x64/app.deb',
                             'apps/desktop/release/macos/arm64/release0.zip',
                             'apps/desktop/release/linux/x64/.secret'):
                file = root / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'file')
            old = Path.cwd()
            os.chdir(root)
            try:
                names = artifact.artifact_names('apps/desktop/release/*/*/*')
                self.assertEqual(sorted(name for _, name in names),
                                 ['linux/x64/app.deb', 'macos/arm64/release0.zip'])
                archive = root / 'multi.tar.gz'
                with tarfile.open(archive, 'w:gz') as tar:
                    for file, name in names:
                        tar.add(file, arcname=name)
                artifact.safe_extract(archive, root / 'restored')
                self.assertEqual((root / 'restored/linux/x64/app.deb').read_bytes(), b'file')
                self.assertEqual((root / 'restored/macos/arm64/release0.zip').read_bytes(), b'file')
                self.assertEqual([name for _, name in artifact.artifact_names(
                    'apps/desktop/release/*/*/*\n!**/*.zip')], ['linux/x64/app.deb'])
            finally:
                os.chdir(old)

    def test_rejects_archive_traversal_and_symlink_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'bad.tar.gz'
            destination = Path(folder) / 'output'
            for member_names in (('../escape',), ('link', 'link/owned')):
                with tarfile.open(archive, 'w:gz') as tar:
                    for name in member_names:
                        info = tarfile.TarInfo(name)
                        if name == 'link':
                            info.type = tarfile.SYMTYPE
                            info.linkname = '.'
                        else:
                            info.size = 1
                        tar.addfile(info, io.BytesIO(b'x') if info.isfile() else None)
                with self.assertRaises(ValueError):
                    artifact.safe_extract(archive, destination)
                self.assertFalse(destination.exists())

    def test_symlink_graph_cannot_escape_or_cycle(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'links.tar.gz'
            for links in ({'d/up': '..', 'escape': 'd/up/..'},
                          {'a': 'b', 'b': 'a'}):
                with tarfile.open(archive, 'w:gz') as tar:
                    directory = tarfile.TarInfo('d')
                    directory.type = tarfile.DIRTYPE
                    tar.addfile(directory)
                    for name, linkname in links.items():
                        entry = tarfile.TarInfo(name)
                        entry.type = tarfile.SYMTYPE
                        entry.linkname = linkname
                        tar.addfile(entry)
                destination = Path(folder) / 'unsafe'
                with self.assertRaises(ValueError):
                    artifact.safe_extract(archive, destination)
                self.assertFalse(destination.exists())

            with tarfile.open(archive, 'w:gz') as tar:
                file = tarfile.TarInfo('release0')
                file.size = 1
                tar.addfile(file, io.BytesIO(b'x'))
                for name, linkname in {'first': 'release0', 'second': 'first'}.items():
                    entry = tarfile.TarInfo(name)
                    entry.type = tarfile.SYMTYPE
                    entry.linkname = linkname
                    tar.addfile(entry)
            destination = Path(folder) / 'valid'
            artifact.safe_extract(archive, destination)
            self.assertEqual((destination / 'second').read_bytes(), b'x')

    def test_linux_native_selects_tailnet_for_broker_and_signed_url(self):
        with patch.dict(os.environ, {
            'RUNNER_OS': 'Linux', 'GARAGE_NETWORK': 'tailnet',
            'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://actions.invalid/token',
            'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'ephemeral',
        }), patch.object(artifact, 'request_json', side_effect=[
            {'value': 'oidc'}, {'url': 'https://garage.invalid/file', 'headers': {}}
        ]) as request:
            artifact.presign('put', name='release')
            self.assertEqual(request.call_args.args[0], artifact.BROKERS['tailnet'])
            self.assertTrue(request.call_args.args[1]['tailnet'])
        with patch.dict(os.environ, {'GARAGE_NETWORK': 'invalid'}):
            with self.assertRaisesRegex(ValueError, 'Invalid artifact network'):
                artifact.presign('put', name='release')

    def test_checksum_mismatch_never_extracts(self):
        with tempfile.TemporaryDirectory() as folder:
            class Response(io.BytesIO):
                headers = {'x-amz-meta-sha256': '0' * 64}
                def __enter__(self):
                    return self
                def __exit__(self, *_):
                    self.close()
            with patch.object(artifact, 'presign', return_value={'url': 'https://garage.invalid/object', 'headers': {}}), \
                 patch.object(artifact.urllib.request, 'urlopen', side_effect=lambda *_args, **_kw: Response(b'corrupted')), \
                 patch.dict(os.environ, {'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1'}):
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    artifact.download('plan', Path(folder) / 'output')
            self.assertFalse((Path(folder) / 'output').exists())

    def test_link_keeps_urls_private_and_rejects_browser_headers(self):
        url = 'https://garage.tailnet.invalid/archive?X-Amz-Signature=secret'
        listing = (b'<ListBucketResult><Contents><Key>runs/42/2/storybook-results.tar.gz</Key></Contents>'
                   b'<Contents><Key>runs/42/2/other.tar.gz</Key></Contents></ListBucketResult>')
        with tempfile.TemporaryDirectory() as folder:
            summary = Path(folder) / 'summary'
            for headers in ({}, {'x-required': 'browser-cannot-send-this'}):
                summary.write_text('')
                requests = []

                def broker(endpoint, payload=None, headers=None):
                    if payload is None:
                        return {'value': 'oidc'}
                    requests.append((endpoint, payload))
                    return {'url': 'http://garage.internal.invalid/list', 'headers': {}} if payload['operation'] == 'list' else {'url': url, 'headers': headers_for_get}

                headers_for_get = headers
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, {
                    'RUNNER_OS': 'Linux', 'GARAGE_OPERATION': 'link', 'GARAGE_PATTERN': 'storybook-*',
                    'GARAGE_NAME': '', 'GARAGE_RUN_ID': '42', 'GARAGE_RUN_ATTEMPT': '2',
                    'GITHUB_STEP_SUMMARY': str(summary), 'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://actions.invalid/token',
                    'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'ephemeral',
                }), patch.object(artifact, 'request_json', side_effect=broker), \
                     patch.object(artifact.urllib.request, 'urlopen', return_value=io.BytesIO(listing)), \
                     redirect_stdout(stdout), redirect_stderr(stderr):
                    if headers:
                        with self.assertRaisesRegex(ValueError, 'browser-incompatible headers'):
                            artifact.main()
                    else:
                        artifact.main()
                self.assertNotIn(url, stdout.getvalue() + stderr.getvalue())
                self.assertEqual(url in summary.read_text(), not bool(headers))
                self.assertEqual([call[1]['operation'] for call in requests], ['list', 'get'])
                self.assertEqual([call[1]['tailnet'] for call in requests], [False, True])
                self.assertEqual(requests[1][1]['name'], 'storybook-results')



if __name__ == '__main__':
    unittest.main()
