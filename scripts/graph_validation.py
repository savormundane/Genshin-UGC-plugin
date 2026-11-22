"""Read-only adapter for Ayaya's strict Graph Code parser and validation rules."""
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from authoring_io import sha_file


class GraphBuildError(ValueError):
    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


def validate_rules(source, runtime, cache=None):
    sys.path.insert(0, str(runtime))
    from engine.configs.settings import settings
    from engine.graph.graph_code_parser import GraphParseError
    from engine.utils.workspace import init_settings_for_workspace
    from engine.validate.api import validate_files
    from engine.validate.node_graph_validation_utils import _parse_line_span, strict_parse_file

    init_settings_for_workspace(workspace_root=runtime, load_user_settings=False)
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
        for issue in validate_files([source], runtime, use_cache=False).issues:
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
    return {'status':'failed' if any(d['severity']=='error' for d in diagnostics) else 'passed',
            'diagnostics':diagnostics}


def check(source):
    from node_build import RUNTIME, metadata

    source = Path(source).resolve()
    digest = None
    try:
        if source.suffix.lower()!='.py' or not source.is_file():
            raise ValueError('Graph check requires a Graph Code .py file')
        digest = sha_file(source)
        metadata(source)
        with tempfile.TemporaryDirectory(prefix='qianxing-graph-check-') as cache:
            proc = subprocess.run(
                [sys.executable,'-X','utf8','-B',__file__,'--worker',str(source),str(RUNTIME),cache],
                cwd=RUNTIME,capture_output=True,text=True,encoding='utf-8',timeout=180,
            )
        if not proc.stdout.strip():
            raise ValueError(proc.stderr.strip()[-3000:] or 'Graph validator did not return a report')
        report = json.loads(proc.stdout)
        if sha_file(source)!=digest:
            raise ValueError('Graph source changed during the check')
    except GraphBuildError as exc:
        report = {'status':'failed','diagnostics':exc.diagnostics}
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        report = {'status':'failed','diagnostics':[{
            'code':'graph_check_failed','severity':'error','message':str(exc),'source':str(source),
        }]}
    report.update(schema=1,scope='single_file',source=str(source),source_sha256=digest,checks={
        'single_file':{'status':report['status']},
        'project_resources':{'status':'not_checked',
                             'message':'Run build with the project resources to check external dependencies and native output.'},
    })
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog='qianxing.py graph',description=__doc__)
    sub = parser.add_subparsers(dest='operation',required=True)
    sub.add_parser('check',help='Validate one Graph Code file without exporting').add_argument('source')
    args = parser.parse_args(argv)
    report = check(args.source)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='passed' else 2


if __name__=='__main__':
    if sys.argv[1:2]==['--worker']:
        with redirect_stdout(sys.stderr):
            report = validate_rules(*map(Path,sys.argv[2:]))
        print(json.dumps(report,ensure_ascii=False))
        raise SystemExit(0 if report['status']=='passed' else 2)
    raise SystemExit(main())
