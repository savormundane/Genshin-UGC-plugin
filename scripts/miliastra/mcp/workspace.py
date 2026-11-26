"""Resolve the file boundary once for each MCP request."""

import os
from pathlib import Path
import stat
from urllib.parse import urlsplit
from urllib.request import url2pathname

from authoring_io import DiagnosticError, PLUGIN, read_json, sha


def linked(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def linked_path_error(path: Path, detail: str) -> DiagnosticError:
    return DiagnosticError(
        'io.linked_path',
        f'路径经过目录联接（junction）、符号链接或其他重解析点。触发位置为 {path}。'
        '请在客户端选择文件夹的实际位置，或使用实际位置重新配置工程和输出目录后重试。',
        source=str(path),
        detail=detail,
    )


def directory(value: str | Path, *, create: bool = False) -> Path:
    path = Path(os.path.abspath(value))
    for part in (path, *path.parents):
        if linked(part):
            raise linked_path_error(part, 'Linked workspace or output directory refused')
    if not path.is_dir() and (not create or path.exists()):
        raise DiagnosticError(
            'io.directory_unavailable',
            f'无法打开目录 {path}。请确认该路径指向已有文件夹后重新选择。',
            source=str(path),
            detail='Directory does not exist or is not a directory: ' + str(path),
        )
    return path.resolve()


def data_directory() -> Path | None:
    value = os.environ.get('MILIASTRA_WONDERLAND_PLUGIN_DATA')
    if value and Path(value).is_absolute():
        return Path(value)
    root = os.environ.get('MILIASTRA_WONDERLAND_INSTALL_ROOT')
    if root and Path(root).is_absolute():
        return Path(root)
    local = os.environ.get('LOCALAPPDATA')
    return Path(local) / 'Miliastra Wonderland' if local and Path(local).is_absolute() else None


def runtime_workspace(data):
    configured = os.environ.get('MILIASTRA_WONDERLAND_RUNTIME_CONFIG')
    path = Path(configured) if configured else data / 'runtime.json' if data else None
    if path is None or not configured and not path.exists():
        return {}
    if not path.is_absolute():
        raise ValueError('MILIASTRA_WONDERLAND_RUNTIME_CONFIG must be an absolute path')
    record = read_json(path)
    if (
        not isinstance(record, dict)
        or type(record.get('schema')) is not int
        or record['schema'] != 1
    ):
        raise ValueError('Invalid runtime binding')
    for field in ('project_root', 'output_root'):
        value = record.get(field)
        if value is not None and (not isinstance(value, str) or not Path(value).is_absolute()):
            raise ValueError('Runtime binding needs an absolute ' + field)
    return record


def workspace(project, output, roots=(), arguments=None):
    data = data_directory()
    record = {}
    config_error = None
    try:
        if not output or not project and not roots:
            record = runtime_workspace(data)
    except (OSError, ValueError, RuntimeError) as exc:
        config_error = str(exc)
    context = {
        'status': 'unconfigured',
        'project_root': None,
        'output_root': None,
        'source': None,
        'output_source': None,
        'candidates': [],
        'missing': ['project_root', 'output_root'],
    }
    try:
        candidates = []
        if project:
            selected = directory(project)
            source = 'explicit'
        elif roots:
            rejected_directory = None
            for uri in roots:
                try:
                    location = urlsplit(uri)
                    if (
                        location.scheme != 'file'
                        or location.netloc
                        or location.query
                        or location.fragment
                    ):
                        continue
                    path = Path(url2pathname(location.path))
                    if not path.is_absolute():
                        continue
                    mounted = directory(path)
                    if mounted != Path(mounted.anchor) and mounted not in candidates:
                        candidates.append(mounted)
                except DiagnosticError as exc:
                    if rejected_directory is None:
                        rejected_directory = exc
                except (OSError, ValueError, RuntimeError):
                    continue
            context['candidates'] = [str(path) for path in candidates]
            if not candidates:
                if rejected_directory is not None:
                    raise rejected_directory
                raise ValueError('MCP client supplied no usable local workspace directory')
            if len(candidates) > 1:
                arguments = arguments or {}
                value = next(
                    (
                        arguments[key]
                        for key in ('input', 'spec', 'other', 'before', 'catalogue')
                        if isinstance(arguments.get(key), str)
                        and Path(arguments[key]).is_absolute()
                    ),
                    None,
                )
                path = Path(os.path.abspath(value)) if value else None
                # A previous output may itself be the primary input of the next request.
                matches = [
                    candidate
                    for candidate in candidates
                    if path
                    and (
                        path.is_relative_to(candidate)
                        or data
                        and path.is_relative_to(workspace_outputs(data, candidate))
                    )
                ]
                if len(matches) != 1:
                    return {
                        **context,
                        'status': 'ambiguous',
                        'source': 'mcp_roots',
                        'message': '会话中有多个工程目录。请提供能定位到其中一个已授权工程的输入文件绝对路径后重试。',
                        'detail': 'Use an absolute input path identifying one authorized workspace',
                    }
                (selected,) = matches
            else:
                (selected,) = candidates
            source = 'mcp_roots'
        elif record.get('project_root'):
            selected = directory(record['project_root'])
            source = 'runtime_config'
        else:
            if config_error:
                raise ValueError(config_error)
            return {
                **context,
                'message': '尚未绑定工程目录。请在客户端打开并授权工程目录，或在启动客户端的终端将 MILIASTRA_WONDERLAND_PROJECT_ROOT 设为工程的绝对路径。已有 runtime.json 时可填写 project_root 后重试。',
                'detail': 'Open a workspace in an MCP client that provides Roots, or set a project in runtime.json or MILIASTRA_WONDERLAND_PROJECT_ROOT',
            }
        if selected == Path(selected.anchor):
            raise ValueError('Project root must be a specific directory')
    except (OSError, ValueError, RuntimeError) as exc:
        if isinstance(exc, DiagnosticError):
            problem, = exc.diagnostics
            return {
                **context,
                'status': 'invalid',
                'message': problem['message'],
                'detail': problem['detail'],
                'directory_problem': {'code': problem['code'], 'source': problem['source']},
            }
        return {
            **context,
            'status': 'invalid',
            'message': '无法使用当前工程目录。请确认目录存在并已在客户端授权，或检查 MILIASTRA_WONDERLAND_PROJECT_ROOT 与 runtime.json 中的 project_root。修正后重试。',
            'detail': str(exc),
        }

    context.update(
        status='ready', project_root=str(selected), source=source, missing=['output_root']
    )
    runtime_project = record.get('project_root')
    configured = output or (
        record.get('output_root')
        if not runtime_project or Path(runtime_project) == selected
        else None
    )
    if not configured and data is None:
        context['output_message'] = (
            '缺少输出根目录。请在启动客户端的终端设置 MILIASTRA_WONDERLAND_OUTPUT_ROOT，'
            '或为插件配置本地数据目录后重试。'
        )
        context['output_detail'] = 'Set MILIASTRA_WONDERLAND_OUTPUT_ROOT or use a local plugin data directory'
        return context
    try:
        target = directory(configured or workspace_outputs(data, selected), create=not configured)
        if any(
            target.is_relative_to(owner) or owner.is_relative_to(target)
            for owner in [selected, PLUGIN, *candidates]
        ):
            raise DiagnosticError(
                'io.output_root_overlap',
                f'输出根目录 {target} 与工程目录或插件目录重叠。请在两者之外选择单独的文件夹后重试。',
                source=str(target),
                detail='Output directory must be separate from workspace and plugin source',
            )
    except DiagnosticError as exc:
        problem, = exc.diagnostics
        context.update(
            output_message=problem['message'],
            output_detail=problem['detail'],
            directory_problem={'code': problem['code'], 'source': problem['source']},
        )
        return context
    except (OSError, ValueError, RuntimeError) as exc:
        context.update(
            output_message='无法使用输出根目录。请检查文件夹位置与访问权限，再重新选择输出目录。',
            output_detail=str(exc),
        )
        return context
    context.update(
        output_root=str(target),
        missing=[],
        output_source='explicit' if output else 'runtime_config' if configured else 'plugin_data',
    )
    return context


def workspace_outputs(data, project):
    name = sha(os.path.normcase(str(project)).encode())[:20]
    return data / 'outputs' / name
