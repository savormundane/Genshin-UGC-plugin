"""Read the public Python runtime contract and probe an existing interpreter."""
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import json
import platform
import re
import sys
import tomllib


PROJECT = tomllib.loads((Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text(encoding='utf-8'))['project']
PYTHON_RANGE = PROJECT['requires-python']
PYTHON_MIN, PYTHON_MAX = ((3, int(minor)) for minor in re.fullmatch(r'>=3\.(\d+),<3\.(\d+)', PYTHON_RANGE).groups())
REQUIREMENTS = dict((name.lower(), required) for name, required in
                    (dependency.split('==', 1) for dependency in PROJECT['dependencies']))


def supported_python(version_info):
    return PYTHON_MIN <= tuple(version_info[:2]) < PYTHON_MAX


def probe():
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64') or sys.maxsize < 2**32:
        raise ValueError('The complete plugin requires Windows x64')
    if platform.python_implementation() != 'CPython' or not supported_python(sys.version_info):
        raise ValueError(f'CPython {PYTHON_RANGE} required')
    mismatches = []
    for name, expected in REQUIREMENTS.items():
        try:
            actual = version(name)
        except PackageNotFoundError:
            actual = 'missing'
        if actual != expected:
            mismatches.append(f'{name}=={expected} (found {actual})')
    if mismatches:
        raise ValueError('Python dependencies: ' + ', '.join(mismatches))
    import mcp.server
    import lupa.lua53
    import PIL.Image
    return sys.executable


if __name__ == '__main__':
    try:
        print(json.dumps(probe()))
    except (ImportError, OSError, ValueError) as error:
        sys.exit(str(error))
