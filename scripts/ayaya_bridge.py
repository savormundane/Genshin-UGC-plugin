"""Bundled offline Ayaya CLI. Plans by default; no GUI, OCR or game automation."""
from functools import lru_cache
from pathlib import Path
import ast
import argparse
import json
import re
import subprocess
import sys

PLUGIN = Path(__file__).resolve().parents[1]
RUNTIME = PLUGIN / 'vendor/ayaya'
FILE_TOOLS = Path('private_extensions/ugc_file_tools')
FILE_TOOLS_RUNNER = Path('private_extensions/run_ugc_file_tools.py')
SHARED_RESOURCES = Path('assets/资源库/共享')
NODE_IMPLEMENTATIONS = Path('plugins/nodes')


TOOLS = (
    'parse_gia_to_graph_ir', 'gia_to_readable_json',
    'export_graph_ir_from_package', 'generate_graph_code_from_package',
    'export_graph_model_json_from_graph_code', 'export_project_graphs_to_gia',
    'gia_graph_ir_to_gia', 'export_ui_workbench_bundles_from_html',
    'check_graph_variable_writeback_contract',
)
REQUIRED = ('app/cli/graph_tools.py', 'engine/graph/graph_code_parser.py',
            FILE_TOOLS_RUNNER, FILE_TOOLS / 'unified_cli/__init__.py')


def compiler_nodes(scope):
    for folder in ('client', 'server') if scope == 'all' else (scope,):
        for path in sorted((RUNTIME / NODE_IMPLEMENTATIONS / folder).rglob('*.py')):
            parsed = ast.parse(path.read_text(encoding='utf-8-sig'))
            for function in parsed.body:
                if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for declaration in function.decorator_list:
                    if not isinstance(declaration, ast.Call) or getattr(declaration.func, 'id', '') != 'node_spec':
                        continue
                    metadata = {}
                    for keyword in declaration.keywords:
                        try:
                            metadata[keyword.arg] = ast.literal_eval(keyword.value)
                        except (ValueError, TypeError):
                            continue
                    yield folder, function.name, ast.unparse(function.args), metadata, path, declaration.lineno


@lru_cache(maxsize=1)
def native_node_catalogue():
    index = json.loads((RUNTIME / FILE_TOOLS / 'node_data/index.json').read_text(encoding='utf-8-sig'))
    return {row['ID']: row for row in index['NodesList']}, {
        row['Expression']: row['ID'] for row in index['TypesList']
    }


def native_semantic_mapping():
    path = RUNTIME / FILE_TOOLS / 'graph_ir/node_type_semantic_map.json'
    return json.loads(path.read_text(encoding='utf-8-sig'))


def resource_definition(path, *, id_name, payload_name):
    runtime = str(RUNTIME)
    if runtime not in sys.path:
        sys.path.insert(0, runtime)
    from engine.resources.definition_schema_view import _try_extract_id_and_payload_from_code

    return _try_extract_id_and_payload_from_code(path, id_name=id_name, payload_name=payload_name)


def signal_literal_diagnostics(source, workspace):
    from engine.graph.common import SIGNAL_NAME_PORT_NAME
    from engine.signal import get_default_signal_repository
    from engine.validate.context import ValidationContext
    from engine.validate.node_semantics import SEMANTIC_SIGNAL_SEND, is_semantic_node_call
    from engine.validate.rules.ast_utils import get_cached_module, infer_graph_scope, iter_class_methods
    from engine.validate.rules.code_structure.signal_param_names import (
        _collect_module_constant_strings, _extract_signal_name_from_value,
    )

    # The exporter resolves these dynamic ports after the ordinary port rules.
    literal_types={'整数':(int,),'浮点数':(int,float),'布尔值':(bool,),'字符串':(str,)}
    context=ValidationContext(workspace_path=workspace,file_path=source)
    tree=get_cached_module(context)
    scope=infer_graph_scope(context)
    names=_collect_module_constant_strings(tree)
    repo=get_default_signal_repository()
    for _,method in iter_class_methods(tree):
        for node in ast.walk(method):
            if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name):
                continue
            if not is_semantic_node_call(workspace_path=workspace,scope=scope,call_name=node.func.id,
                                         semantic_id=SEMANTIC_SIGNAL_SEND):
                continue
            keywords={kw.arg:kw.value for kw in node.keywords}
            name=_extract_signal_name_from_value(keywords.get(SIGNAL_NAME_PORT_NAME),names)
            signal_id=repo.resolve_id_by_name(name)
            if not signal_id:
                continue  # The regular signal-name rule owns unresolved definitions.
            payload=repo.get_payload(signal_id)
            for field in payload.get('parameters') or ():
                port,expected=field['name'],field['parameter_type']
                value=keywords.get(port)
                is_list=expected.endswith('列表')
                types=literal_types.get(expected.removesuffix('列表'))
                if value is None or types is None:
                    continue
                try:
                    actual=ast.literal_eval(value)
                except (TypeError,ValueError):
                    continue  # The ordinary parser owns types of connected expressions.
                valid=(type(actual) is list and all(type(item) in types for item in actual)
                       if is_list else type(actual) in types)
                if not valid:
                    yield {'code':'graph.signal_literal_type','severity':'error',
                           'message':f"Signal {name!r} port {port!r} expects {expected}",
                           'source':str(source),'line':value.lineno,'port':port,'expected':expected,
                           'actual':type(actual).__name__,'signal':name}


def validate_rules(source, runtime, cache=None, workspace=None):
    sys.path.insert(0, str(runtime))
    from engine.configs.settings import settings
    from engine.graph.graph_code_parser import GraphParseError
    from engine.utils.workspace import init_settings_for_workspace
    from engine.validate.api import validate_files
    from engine.validate.node_graph_validation_utils import _parse_line_span, strict_parse_file

    root = workspace if workspace is not None else runtime
    init_settings_for_workspace(workspace_root=root, load_user_settings=False)
    if workspace is not None:
        from engine.utils.runtime_scope import set_active_package_id
        from engine.resources.definition_schema_view import set_default_definition_schema_view_active_package_id
        from engine.resources.level_variable_schema_view import set_default_level_variable_schema_view_active_package_id
        from engine.resources.ingame_save_template_schema_view import set_default_ingame_save_template_schema_view_active_package_id

        set_active_package_id('BuildProject')
        set_default_definition_schema_view_active_package_id('BuildProject')
        set_default_level_variable_schema_view_active_package_id('BuildProject')
        set_default_ingame_save_template_schema_view_active_package_id('BuildProject')
    if cache is not None:
        settings.RUNTIME_CACHE_ROOT = str(cache)
    diagnostics = []
    try:
        strict_parse_file(source)
    except GraphParseError as exc:
        diagnostics.append({'code':'strict_graph_parse','severity':'error','message':str(exc),
                            'source':str(source),'line':exc.line_number})
    except SyntaxError as exc:
        diagnostics.append({'code':'graph_syntax','severity':'error','message':exc.msg,
                            'source':str(source),'line':exc.lineno})
    else:
        for issue in validate_files([source], root, use_cache=False).issues:
            item = {'code':issue.code or 'graph_validation','severity':issue.level,
                    'message':issue.message,'source':issue.file or str(source)}
            span = _parse_line_span(issue.line_span)
            if span:
                item.update(line=span.start, end_line=span.end)
            if issue.port:
                item['port'] = issue.port
            if issue.code=='PORT_TYPE_MISMATCH':
                types = re.search(r"期望类型『([^』]+)』，实际传入类型『([^』]+)』", issue.message)
                if types:
                    item.update(expected=types[1],actual=types[2])
                port = re.search(r"输入端口 '([^']+)'", issue.message)
                if port:
                    item['port'] = port[1]
            diagnostics.append(item)
        if not any(d['severity']=='error' for d in diagnostics):
            diagnostics.extend(signal_literal_diagnostics(source,root))
    return {'status':'failed' if any(d['severity']=='error' for d in diagnostics) else 'passed',
            'diagnostics':diagnostics}


def build_plan(args):
    repo = Path(args.repo).expanduser().resolve()
    missing = [str(p) for p in REQUIRED if not (repo / p).is_file()]
    if missing:
        raise ValueError('Incomplete tool repository: ' + ', '.join(missing))
    extra = list(args.extra)
    if extra[:1] == ['--']:
        extra = extra[1:]
    forbidden = {'--fix', '--inject-target-gil', '--inject-skip-non-empty-check',
                 '--no-inject-create-backup', '--skip-precheck', '--non-strict',
                 '--allow-unresolved-ui-keys'}
    if any(x.split('=', 1)[0] in forbidden for x in extra):
        raise ValueError('Adapter excludes in-place mutation and validation bypass flags')
    python = str(Path(args.python).expanduser().resolve())
    if not Path(python).is_file():
        raise ValueError('--python must identify an existing interpreter executable')
    command = [python, '-X', 'utf8', '-B']
    if args.action == 'doctor':
        return {'repo': str(repo), 'required_entries_present': True,
                'external_tools': list(TOOLS), 'runtime_dependencies_tested': False}
    if args.action in ('validate-file', 'validate-project', 'validate-ui'):
        command += ['-m', 'app.cli.graph_tools', args.action]
        if args.action == 'validate-file':
            if not args.input:
                raise ValueError('validate-file requires --input')
            command += [str(Path(args.input).resolve()), '--strict']
        elif args.package_id:
            command += ['--package-id', args.package_id]
    elif args.action == 'tool':
        if not args.tool:
            raise ValueError('tool requires --tool')
        command += [str(repo / FILE_TOOLS_RUNNER), 'tool', args.tool]
    elif args.action == 'project-import':
        if not all((args.input, args.output, args.project)):
            raise ValueError('project-import requires --input, --output and --project')
        source, output = Path(args.input).resolve(), Path(args.output).resolve()
        if not source.is_file() or output.exists() or source == output:
            raise ValueError('Use an existing input and a new, different output file')
        command += [str(repo / FILE_TOOLS_RUNNER), 'project', 'import',
                    '--dangerous', '--project-archive', str(Path(args.project).resolve()),
                    '--graphs-strict', str(source), str(output)]
    command += extra
    return {'cwd': str(repo), 'argv': command, 'executed': False,
            'note': 'Upstream may write outputs/caches in its own workspace; inspect reported paths.'}

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', default=str(RUNTIME), help='Bundled tool root; optional explicit override')
    p.add_argument('--python', default=sys.executable, help='Interpreter executable, not a shell command')
    p.add_argument('--execute', action='store_true', help='Run the planned offline CLI operation')
    p.add_argument('--timeout', type=int, default=300)
    p.add_argument('--input'); p.add_argument('--output'); p.add_argument('--project')
    p.add_argument('--package-id'); p.add_argument('--tool', choices=TOOLS)
    p.add_argument('action', choices=['doctor','validate-file','validate-project','validate-ui','tool','project-import'])
    p.add_argument('extra', nargs=argparse.REMAINDER, help='Upstream arguments after --')
    args = p.parse_args(argv)
    try:
        plan = build_plan(args)
        if args.action == 'doctor' or not args.execute:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        return subprocess.run(plan['argv'], cwd=plan['cwd'], timeout=args.timeout,
                              shell=False, check=False).returncode
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
