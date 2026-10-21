#!/usr/bin/env python3
"""Run with python3 -m unittest discover -s tests -p 'test_garage_artifact.py'."""
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
                             'apps/desktop/release/macos/arm64/app.zip',
                             'apps/desktop/release/linux/x64/.secret'):
                file = root / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b'file')
            old = Path.cwd()
            os.chdir(root)
            try:
                names = artifact.artifact_names('apps/desktop/release/*/*/*\n!**/*.zip')
            finally:
                os.chdir(old)
            self.assertEqual([name for _, name in names], ['linux/x64/app.deb'])

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


if __name__ == '__main__':
    unittest.main()
