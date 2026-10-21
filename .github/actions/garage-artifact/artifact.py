#!/usr/bin/env python3
"""Attempt-scoped Garage artifacts; only the broker receives the GitHub OIDC token."""
import fnmatch
import glob
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

AUDIENCE = 'garage-ci-artifacts'
BROKERS = {
    'Linux': 'http://nx-cache.nx-cache.svc.cluster.local:3000/artifacts/presign',
    'macOS': 'https://nx-cache.taile99f5b.ts.net/artifacts/presign',
    'Windows': 'https://nx-cache.taile99f5b.ts.net/artifacts/presign',
}
CHUNK = 1024 * 1024


def request_json(url, payload=None, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                                 headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def presign(operation, **options):
    token_url = os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
    separator = '&' if '?' in token_url else '?'
    oidc = request_json(token_url + separator + urllib.parse.urlencode({'audience': AUDIENCE}),
                        headers={'Authorization': 'Bearer ' + os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']})['value']
    payload = {'operation': operation, 'purpose': os.environ.get('GARAGE_PURPOSE', 'ci'),
               'tailnet': os.environ.get('RUNNER_OS', 'Linux') != 'Linux'}
    payload.update({key: value for key, value in options.items() if value is not None})
    return request_json(os.environ.get('GARAGE_BROKER_URL') or BROKERS[os.environ.get('RUNNER_OS', 'Linux')],
                        payload, {'Authorization': 'Bearer ' + oidc, 'Content-Type': 'application/json'})


def artifact_names(patterns, hidden=False):
    """GitHub artifact glob roots: the directory before the first wildcard is retained."""
    includes, excludes = [], []
    for line in patterns.splitlines():
        pattern = line.strip()
        if not pattern:
            continue
        if pattern.startswith('!'):
            excludes.append(pattern[1:])
            continue
        wildcard = next((i for i, c in enumerate(pattern) if c in '*?['), len(pattern))
        root = (Path(pattern[:wildcard].rstrip('/')) if pattern[:wildcard].endswith('/')
                else Path(pattern[:wildcard]).parent) if wildcard < len(pattern) else (
                    Path(pattern) if Path(pattern).is_dir() else Path(pattern).parent)
        matches = glob.glob(pattern, recursive=True)
        if hidden and wildcard < len(pattern):
            matches.extend(str(candidate) for candidate in root.rglob('*')
                           if fnmatch.fnmatchcase(str(candidate), pattern))
        for match in matches:
            path = Path(match)
            if path.is_dir() and not path.is_symlink():
                entries = (p for p in path.rglob('*') if p.is_file() or p.is_symlink())
            else:
                entries = (path,)
            for entry in entries:
                if (entry.is_file() or entry.is_symlink()) and (hidden or not any(
                        part.startswith('.') for part in entry.relative_to(root).parts)):
                    includes.append((entry, root))
    files = {}
    for entry, root in includes:
        if not any(fnmatch.fnmatch(str(entry), pat) for pat in excludes):
            files[entry.resolve(strict=False) if not entry.is_symlink() else entry.absolute()] = (entry, root)
    if not files:
        return []
    # Shared root keeps multiline patterns' parent structure, while a single path
    # (including an explicit directory) has the same contents-at-root semantics.
    roots = [str(root.absolute()) for _, root in files.values()]
    common = Path(os.path.commonpath(roots))
    return [(entry, entry.absolute().relative_to(common).as_posix()) for entry, _ in files.values()]


def digest_file(path):
    sha = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(CHUNK), b''):
            sha.update(block)
    return sha.hexdigest()


def upload(name, paths, missing='warn', hidden=False):
    files = artifact_names(paths, hidden)
    if not files:
        if missing == 'error':
            raise ValueError('No files matched upload paths')
        if missing == 'warn':
            print('::warning::No files matched upload paths')
        return
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / 'artifact.tar.gz'
        with tarfile.open(archive, 'w:gz', dereference=False) as tar:
            for file, relative in sorted(files, key=lambda pair: pair[1]):
                tar.add(file, arcname=relative, recursive=False)
        size = archive.stat().st_size
        if size > 5 * 1024**3:
            raise ValueError('Artifact exceeds 5 GiB limit')
        sha = digest_file(archive)
        signed = presign('put', name=name, sha256=sha, size=size)
        with archive.open('rb') as source:
            req = urllib.request.Request(signed['url'], source, headers=signed['headers'], method='PUT')
            with urllib.request.urlopen(req, timeout=300) as response:
                if response.status not in (200, 201, 204):
                    raise ValueError('Artifact upload failed')
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write(f'artifact-digest={sha}\n')


def safe_extract(archive, destination):
    """Preflight every member before any write; symlinks cannot parent another member."""
    destination = Path(destination).resolve()
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        names = set()
        links = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (not member.name or path.as_posix() == '.' or path.is_absolute() or '..' in path.parts
                    or any(c in member.name for c in ('\\', ':', '\x00')) or not (
                        member.isfile() or member.isdir() or member.issym()) or path.as_posix() in names):
                raise ValueError('Unsafe archive entry')
            names.add(path.as_posix())
            target = destination.joinpath(*path.parts)
            if not target.is_relative_to(destination) or any(p.is_symlink() for p in (target, *target.parents) if p != destination):
                raise ValueError('Unsafe extraction destination')
            if member.issym():
                link = (target.parent / member.linkname).resolve(strict=False)
                if not link.is_relative_to(destination) or os.path.isabs(member.linkname):
                    raise ValueError('Archive symlink escapes destination')
                links.add(path.as_posix())
        if any(any(PurePosixPath(name).is_relative_to(PurePosixPath(link)) and name != link
                   for link in links) for name in names):
            raise ValueError('Archive member beneath symlink')
        destination.mkdir(parents=True, exist_ok=True)
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, open(target, 'wb') as sink:
                    shutil.copyfileobj(source, sink, CHUNK)
                target.chmod(member.mode & 0o777)
        for member in members:
            if member.issym():
                target = destination.joinpath(*PurePosixPath(member.name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(member.linkname)
        for member in reversed(members):
            if member.isdir():
                destination.joinpath(*PurePosixPath(member.name).parts).chmod(member.mode & 0o777)


def list_names(run_id, run_attempt):
    names, continuation = [], None
    while True:
        signed = presign('list', runId=run_id, runAttempt=run_attempt, continuationToken=continuation)
        req = urllib.request.Request(signed['url'], headers=signed['headers'])
        with urllib.request.urlopen(req, timeout=60) as response:
            root = ET.parse(response).getroot()
        prefix = f'runs/{run_id}/{run_attempt}/'
        for element in root.findall('.//{*}Contents/{*}Key'):
            key = element.text or ''
            if key.startswith(prefix) and key.endswith('.tar.gz'):
                names.append(key[len(prefix):-7])
        truncated = root.findtext('.//{*}IsTruncated') == 'true'
        continuation = root.findtext('.//{*}NextContinuationToken')
        if not truncated:
            break
        if not continuation:
            raise ValueError('Incomplete artifact listing')
    return names


def download(name, path, pattern='', merge=False, run_id=None, run_attempt=None, expected_digest=''):
    run_id = run_id or os.environ['GITHUB_RUN_ID']
    run_attempt = run_attempt or os.environ['GITHUB_RUN_ATTEMPT']
    if name:
        names = [name]
    else:
        names = [item for item in list_names(run_id, run_attempt) if not pattern or fnmatch.fnmatchcase(item, pattern)]
    if not names:
        raise ValueError('No artifacts matched requested name/pattern')
    if expected_digest and len(names) != 1:
        raise ValueError('Expected digest requires a single artifact')
    for item in names:
        signed = presign('get', name=item, runId=run_id, runAttempt=run_attempt)
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'artifact.tar.gz'
            sha = hashlib.sha256()
            req = urllib.request.Request(signed['url'], headers=signed['headers'])
            with urllib.request.urlopen(req, timeout=300) as response, archive.open('wb') as sink:
                expected = response.headers.get('x-amz-meta-sha256')
                if not expected or len(expected) != 64:
                    raise ValueError('Artifact checksum metadata missing')
                for block in iter(lambda: response.read(CHUNK), b''):
                    sha.update(block)
                    sink.write(block)
            if sha.hexdigest() != expected or (expected_digest and sha.hexdigest() != expected_digest):
                raise ValueError('Artifact checksum mismatch')
            safe_extract(archive, Path(path) / item if len(names) > 1 and not merge else path)
            if len(names) == 1:
                with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                    output.write(f'artifact-digest={sha.hexdigest()}\n')


def main():
    env = os.environ
    operation = env['GARAGE_OPERATION']
    name = env.get('GARAGE_NAME', '')
    if env.get('GARAGE_PURPOSE', 'ci') not in ('ci', 'recovery'):
        raise ValueError('Invalid artifact purpose')
    if operation == 'upload':
        if not name:
            raise ValueError('Artifact name is required on upload')
        missing = env.get('GARAGE_MISSING', 'warn')
        if missing not in ('warn', 'ignore', 'error'):
            raise ValueError('Invalid if-no-files-found value')
        upload(name, env['GARAGE_PATH'], missing, env.get('GARAGE_HIDDEN') == 'true')
    elif operation == 'download':
        if env.get('GARAGE_RUN_ID') and not env.get('GARAGE_RUN_ATTEMPT'):
            raise ValueError('Explicit run-id requires explicit run-attempt')
        download(name, env['GARAGE_PATH'], env.get('GARAGE_PATTERN', ''), env.get('GARAGE_MERGE') == 'true',
                 env.get('GARAGE_RUN_ID') or None, env.get('GARAGE_RUN_ATTEMPT') or None,
                 env.get('GARAGE_EXPECTED_DIGEST', ''))
    else:
        raise ValueError('Invalid operation')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # urllib exceptions may include presigned URLs or bearer tokens: never print them.
        print(f'::error::{error}' if isinstance(error, (ValueError, KeyError)) else '::error::Garage artifact transfer failed', file=sys.stderr)
        sys.exit(1)
