"""Read-only adapter for Ayaya's strict Graph Code parser and validation rules."""
import argparse
import ast
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from authoring_io import DiagnosticError, ProductionInputs, read_json, sha


class GraphBuildError(ValueError):
    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


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


def check(source, bindings_path=None, job_path=None):
    from node_build import RUNTIME, metadata
    from native_bindings import Bindings, expand_graph, read_bindings

    source = Path(source).resolve()
    inputs = ProductionInputs()
    digest = binding_digest = None
    pending_bindings = False
    binding_identity = 'not_checked'
    try:
        if source.suffix.lower()!='.py' or not source.is_file():
            raise ValueError('Graph check requires a Graph Code .py file')
        original = source.read_bytes()
        digest = sha(original)
        inputs.bind(source,digest,'graph_check')
        code = original.decode('utf-8-sig')
        meta = metadata(source,code)
        with tempfile.TemporaryDirectory(prefix='qianxing-graph-check-') as cache:
            cache = Path(cache)
            workspace = None
            workspace_args = []
            baseline_path = None
            if job_path is not None:
                from graph_resources import prepare_check_context

                workspace = cache/'project'
                project, graphs, job_bindings, baseline_path, pending_bindings = prepare_check_context(
                    Path(job_path).resolve(),workspace,inputs)
                declared = graphs.get(source,{})
                scope = declared.get('scope',meta['graph_type'])
                if scope != meta['graph_type']:
                    raise ValueError('Scope does not match Graph Code metadata')
                category = declared.get('category','技能节点图' if scope=='client' else '')
                if category not in ('','技能节点图','布尔过滤器节点图','整数过滤器节点图','状态节点图'):
                    raise ValueError('Unsupported graph category')
                compiled = project/'节点图'/scope/category/source.name
                compiled.parent.mkdir(parents=True)
                workspace_args = [str(workspace)]
                if bindings_path is None:
                    bindings_path = job_bindings
            else:
                compiled = cache/source.name
            bindings = Bindings()
            if bindings_path is not None:
                bindings_path = Path(bindings_path).resolve()
                baseline=None
                if baseline_path is not None:
                    baseline=baseline_path.read_bytes()
                    inputs.bind(baseline_path,sha(baseline),'graph_bindings')
                bindings, binding_digest = read_bindings(bindings_path,baseline)
                inputs.bind(bindings_path,binding_digest,'graph_bindings')
                if baseline is not None:binding_identity='passed'
            expanded = expand_graph(code,source,bindings)
            if workspace is None and expanded == code:
                compiled = source
            else:
                compiled.write_bytes(expanded.encode('utf-8'))
            worker = [sys.executable,'-X','utf8','-B',__file__,'--worker',str(compiled),str(RUNTIME),str(cache),*workspace_args]
            if os.environ.get('UGC_BUILD_BOUNDARY'):
                worker.insert(4,str(RUNTIME.parents[1]/'scripts/dependency_runner.py'))
            proc = subprocess.run(worker,cwd=RUNTIME,capture_output=True,text=True,encoding='utf-8',timeout=180)
            if not proc.stdout.strip():
                raise ValueError(proc.stderr.strip()[-3000:].replace(str(compiled),str(source)) or
                                 'Graph validator did not return a report')
            report = json.loads(proc.stdout)
            for diagnostic in report['diagnostics']:
                if compiled != source:
                    diagnostic['source'] = str(source)
                    diagnostic['message'] = diagnostic['message'].replace(str(compiled),str(source))
                if job_path is None and diagnostic['code'] in ('CODE_SIGNAL_UNKNOWN_ID','CODE_ON_METHOD_NAME_UNKNOWN'):
                    diagnostic.update(severity='info',status='not_checked')
            if job_path is None:
                report['status'] = ('failed' if any(d['severity']=='error' for d in report['diagnostics']) else
                                    'not_checked' if any(d.get('status')=='not_checked' for d in report['diagnostics']) else 'passed')
        inputs.verify()
    except (GraphBuildError, DiagnosticError) as exc:
        diagnostics = exc.diagnostics
        waiting = pending_bindings and diagnostics[0]['code']=='native.binding_missing'
        if waiting:
            name=diagnostics[0]['object']
            diagnostics[0].update(code='graph.binding_pending',severity='info',status='not_checked',
                                  message=f'Binding {name!r} is pending until the job produces its GIL baseline.')
        report = {'status':'not_checked' if waiting else 'failed','diagnostics':diagnostics}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report = {'status':'failed','diagnostics':[{
            'code':'graph_check_failed','severity':'error','message':str(exc),'source':str(source),
        }]}
    report.update(schema=1,scope='single_file' if job_path is None else 'declared_project',source=str(source),
                  source_sha256=digest,inputs=inputs,checks={
        'single_file':{'status':report['status']},
        'project_resources':{'status':'not_checked' if job_path is None else report['status']},
    })
    if binding_digest is not None:
        report['bindings_sha256'] = binding_digest
        report['checks']['binding_identity']={'status':binding_identity}
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(prog='qianxing.py graph',description=__doc__)
    sub = parser.add_subparsers(dest='operation',required=True)
    action=sub.add_parser('check',help='Validate one Graph Code file without exporting')
    action.add_argument('source')
    action.add_argument('--bindings',help='Use the typed names from a bindings.json file')
    action.add_argument('--job',help='Read the declarations from a production job')
    bind=sub.add_parser('bind',help='Bind typed names to exact GIL object keys')
    bind.add_argument('baseline')
    bind.add_argument('--spec',help='JSON map from typed names to project object keys')
    bind.add_argument('--from',dest='old_gil',help='Rebase names from this prior GIL')
    bind.add_argument('--bindings',help='Schema 2 bindings for --from')
    bind.add_argument('--out',required=True)
    args = parser.parse_args(argv)
    if args.operation=='bind':
        from native_bindings import bind_selectors, rebase_bindings

        if bool(args.old_gil)!=bool(args.bindings) or not (args.old_gil or args.spec):
            bind.error('Provide --spec, or --from and --bindings with optional --spec selections')
        baseline=Path(args.baseline).read_bytes()
        selections=read_json(args.spec) if args.spec else None
        if args.old_gil:
            report,result=rebase_bindings(Path(args.old_gil).read_bytes(),args.bindings,baseline,selections)
            if result is None:
                print(json.dumps(report,ensure_ascii=False,indent=2))
                return 2
        else:
            result=report=bind_selectors(baseline,selections)
        with Path(args.out).open('x',encoding='utf-8') as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2)
            stream.write('\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    report = check(args.source,args.bindings,args.job)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='passed' else 2


if __name__=='__main__':
    if sys.argv[1:2]==['--worker']:
        with redirect_stdout(sys.stderr):
            report = validate_rules(*map(Path,sys.argv[2:]))
        print(json.dumps(report,ensure_ascii=False))
        raise SystemExit(0 if report['status']=='passed' else 2)
    raise SystemExit(main())
