"""Resolve the pinned Windows Canvas payload for Beyond."""

from pathlib import Path
import os
import re
import shutil
import tempfile
from urllib.request import Request, urlopen
import zipfile

from authoring_io import PLUGIN, read_json, sha_file
from miliastra.mcp.workspace import data_directory


LOCK_NAME = 'native-canvas.json'
CANVAS_PACKAGE = 'node_modules/@napi-rs/canvas-win32-x64-msvc/'
NATIVE_BINARY = CANVAS_PACKAGE + 'skia.win32-x64-msvc.node'
NATIVE_FILES = {NATIVE_BINARY, CANVAS_PACKAGE + 'icudtl.dat'}
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
RELEASE_URL = (
    r'https://github\.com/savormundane/miliastra-wonderland-plugin/releases/download/'
    r'beyond-canvas-v(\d+\.\d+\.\d+)/miliastra-beyond-canvas-\1-windows-x64\.zip'
)


def read_native_lock(backend):
    """Validate the delivery identity against the Beyond file manifest."""
    path = backend / LOCK_NAME
    if not path.exists():
        return None
    lock = read_json(path)
    if (not isinstance(lock, dict) or set(lock) != {'schema', 'url', 'sha256', 'files'}
            or type(lock['schema']) is not int or lock['schema'] != 1
            or not isinstance(lock['url'], str) or not re.fullmatch(RELEASE_URL, lock['url'])
            or not isinstance(lock['files'], dict) or set(lock['files']) != NATIVE_FILES
            or any(not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value)
                   for value in (lock['sha256'], *lock['files'].values()))):
        raise ValueError('Invalid Beyond native Canvas lock')
    bundled = read_json(backend / 'bundle.json')['files']
    if any(bundled.get(name) != digest for name, digest in lock['files'].items()):
        raise ValueError('Beyond native Canvas lock differs from the bundled file manifest')
    return lock


def verify_native_files(root, lock):
    """Verify both files together. Return false when neither is available."""
    root = root.resolve()
    paths = {root / name: digest for name, digest in lock['files'].items()}
    if any(path.resolve() != path for path in paths):
        raise ValueError('Linked Beyond native Canvas payload refused')
    present = [path for path in paths if path.exists()]
    if not present:
        return False
    if len(present) != len(paths):
        raise ValueError('Incomplete Beyond native Canvas payload')
    for path, digest in paths.items():
        if not path.is_file() or sha_file(path) != digest:
            raise ValueError(f'Beyond native Canvas file SHA-256 mismatch: {path.name}')
    return True


def download_native_archive(lock, path):
    """Download the versioned release asset to a caller-owned staging path."""
    req = Request(lock['url'], headers={'User-Agent': 'Miliastra-Wonderland'})
    try:
        with urlopen(req, timeout=45) as response, path.open('xb') as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_PAYLOAD_BYTES:
                    raise ValueError('Beyond native Canvas download exceeds size limit')
                output.write(chunk)
    except OSError as error:
        raise ValueError(
            f'Beyond 原生渲染依赖下载失败。请检查 GitHub Release 的网络访问，或使用完整 Windows ZIP。{error}'
        ) from error


def extract_native_archive(lock, archive, destination):
    """Verify archive and payload before publishing a new directory."""
    if archive.stat().st_size > MAX_PAYLOAD_BYTES or sha_file(archive) != lock['sha256']:
        raise ValueError('Beyond native Canvas archive SHA-256 mismatch')
    if destination.exists():
        raise FileExistsError(destination)
    with tempfile.TemporaryDirectory(prefix='native-', dir=destination.parent) as temporary:
        stage = Path(temporary) / 'payload'
        stage.mkdir()
        try:
            with zipfile.ZipFile(archive) as source:
                members = source.infolist()
                if (len(members) != len(lock['files'])
                        or {member.filename for member in members} != lock['files'].keys()
                        or sum(member.file_size for member in members) > MAX_PAYLOAD_BYTES):
                    raise ValueError('Unexpected Beyond native Canvas archive entries')
                for member in members:
                    path = stage / member.filename
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(member) as stream, path.open('xb') as output:
                        shutil.copyfileobj(stream, output)
        except zipfile.BadZipFile as error:
            raise ValueError(f'Invalid Beyond native Canvas ZIP: {error}') from error
        if not verify_native_files(stage, lock):
            raise ValueError('Beyond native Canvas archive is empty')
        stage.rename(destination)


def native_cache_root():
    data = data_directory()
    return data.resolve() / 'beyond-native' if data is not None else None


def native_library_path(backend, *, lock=None):
    """Return a verified bundled or lazily hydrated binding."""
    if lock is None:
        lock = read_native_lock(backend)
    if lock is None:
        return None
    if verify_native_files(backend, lock):
        return backend / NATIVE_BINARY
    staged = os.environ.get('MILIASTRA_WONDERLAND_BEYOND_NATIVE_ROOT')
    if staged:
        path = Path(staged)
        if not path.is_absolute() or not verify_native_files(path, lock):
            raise ValueError('Invalid staged Beyond native Canvas payload')
        return path / NATIVE_BINARY
    root = native_cache_root()
    if root is None:
        raise ValueError('请设置绝对路径 MILIASTRA_WONDERLAND_PLUGIN_DATA 或 LOCALAPPDATA，以缓存 Beyond 原生渲染依赖。')
    cache = root / lock['sha256']
    if (cache.resolve() != cache or cache.is_relative_to(PLUGIN.resolve())
            or cache.is_relative_to(backend.resolve())):
        raise ValueError('Beyond native Canvas cache must be outside the plugin source')
    if cache.exists():
        if not verify_native_files(cache, lock):
            raise ValueError(f'Beyond native Canvas cache is incomplete: {cache}')
        return cache / NATIVE_BINARY
    cache.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='download-', dir=cache.parent) as temporary:
        archive = Path(temporary) / 'canvas.zip'
        download_native_archive(lock, archive)
        try:
            extract_native_archive(lock, archive, cache)
        except OSError:
            if not verify_native_files(cache, lock):
                raise
    return cache / NATIVE_BINARY


def native_canvas_environment(binding):
    env = os.environ.copy()
    if binding is not None:
        env.pop('NAPI_RS_FORCE_WASI', None)
        env['NAPI_RS_NATIVE_LIBRARY_PATH'] = str(binding)
    return env
