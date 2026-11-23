"""Resolve the file boundary once for each MCP request."""

import os
from pathlib import Path
import stat
from urllib.parse import urlsplit
from urllib.request import url2pathname

from authoring_io import PLUGIN, read_json, sha


def linked(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def directory(value, *, create=False):
    path = Path(os.path.abspath(value))
    if any(linked(part) for part in (path, *path.parents)):
        raise ValueError('Linked workspace or output directory refused')
    if not path.is_dir() and (not create or path.exists()):
        raise ValueError('Directory does not exist: ' + str(path))
    return path.resolve()


def data_directory():
    value = os.environ.get('UGC_PLUGIN_DATA')
    if value and Path(value).is_absolute():
        return Path(value)
    root = os.environ.get('MILIASTRA_WONDERLAND_INSTALL_ROOT') or os.environ.get('UGC_PUBLIC_INSTALL_ROOT')
    if root and Path(root).is_absolute():
        return Path(root)
    local = os.environ.get('LOCALAPPDATA')
    return Path(local) / 'Miliastra Wonderland' if local and Path(local).is_absolute() else None


def runtime_workspace(data):
    configured = os.environ.get('UGC_RUNTIME_CONFIG')
    path = Path(configured) if configured else data / 'runtime.json' if data else None
    if path is None or not configured and not path.exists():
        return {}
    if not path.is_absolute():
        raise ValueError('UGC_RUNTIME_CONFIG must be an absolute path')
    record = read_json(path)
    if not isinstance(record, dict) or type(record.get('schema')) is not int or record['schema'] != 1:
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
    context = {'status': 'unconfigured', 'project_root': None, 'output_root': None,
               'source': None, 'output_source': None, 'candidates': [],
               'missing': ['project_root', 'output_root']}
    try:
        candidates = []
        if project:
            selected = directory(project)
            source = 'explicit'
        elif roots:
            for uri in roots:
                try:
                    location = urlsplit(uri)
                    if location.scheme != 'file' or location.netloc or location.query or location.fragment:
                        continue
                    path = Path(url2pathname(location.path))
                    if not path.is_absolute():
                        continue
                    mounted = directory(path)
                    if mounted != Path(mounted.anchor) and mounted not in candidates:
                        candidates.append(mounted)
                except (OSError, ValueError, RuntimeError):
                    continue
            context['candidates'] = [str(path) for path in candidates]
            if not candidates:
                raise ValueError('MCP client supplied no usable local workspace directory')
            if len(candidates) > 1:
                arguments = arguments or {}
                value = next((arguments[key] for key in ('input', 'spec', 'other', 'before', 'catalogue')
                              if isinstance(arguments.get(key), str) and Path(arguments[key]).is_absolute()), None)
                path = Path(os.path.abspath(value)) if value else None
                # A previous output may itself be the primary input of the next request.
                matches = [candidate for candidate in candidates if path and (
                    path.is_relative_to(candidate) or data and
                    path.is_relative_to(workspace_outputs(data, candidate)))]
                if len(matches) != 1:
                    return {**context, 'status': 'ambiguous', 'source': 'mcp_roots',
                            'message': 'Use an absolute input path identifying one authorized workspace'}
                selected, = matches
            else:
                selected, = candidates
            source = 'mcp_roots'
        elif record.get('project_root'):
            selected = directory(record['project_root'])
            source = 'runtime_config'
        else:
            if config_error:
                raise ValueError(config_error)
            return {**context, 'message': 'Open a workspace in an MCP client that provides Roots, or set a project in runtime.json or UGC_PROJECT_ROOT'}
        if selected == Path(selected.anchor):
            raise ValueError('Project root must be a specific directory')
    except (OSError, ValueError, RuntimeError) as exc:
        return {**context, 'status': 'invalid', 'message': str(exc)}

    context.update(status='ready', project_root=str(selected), source=source, missing=['output_root'])
    runtime_project = record.get('project_root')
    configured = output or (record.get('output_root') if not runtime_project or Path(runtime_project) == selected else None)
    if not configured and data is None:
        context['output_message'] = 'Set UGC_OUTPUT_ROOT or use a local plugin data directory'
        return context
    try:
        target = directory(configured or workspace_outputs(data, selected), create=not configured)
        if any(target.is_relative_to(owner) or owner.is_relative_to(target)
               for owner in [selected, PLUGIN, *candidates]):
            raise ValueError('Output directory must be separate from workspace and plugin source')
    except (OSError, ValueError, RuntimeError) as exc:
        context['output_message'] = str(exc)
        return context
    context.update(output_root=str(target), missing=[],
                   output_source='explicit' if output else 'runtime_config' if configured else 'plugin_data')
    return context


def workspace_outputs(data, project):
    name = sha(os.path.normcase(str(project)).encode())[:20]
    return data / 'outputs' / name
