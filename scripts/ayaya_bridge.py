"""Bundled offline Ayaya CLI. Plans by default; no GUI, OCR or game automation."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

TOOLS = (
    'parse_gia_to_graph_ir', 'gia_to_readable_json',
    'export_graph_ir_from_package', 'generate_graph_code_from_package',
    'export_graph_model_json_from_graph_code', 'export_project_graphs_to_gia',
    'gia_graph_ir_to_gia', 'export_ui_workbench_bundles_from_html',
    'check_graph_variable_writeback_contract',
)
REQUIRED = ('app/cli/graph_tools.py', 'engine/graph/graph_code_parser.py',
            'private_extensions/run_ugc_file_tools.py',
            'private_extensions/ugc_file_tools/unified_cli/__init__.py')

def build_plan(args):
    repo = Path(args.repo).expanduser().resolve()
    missing = [p for p in REQUIRED if not (repo / p).is_file()]
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
        command += [str(repo / 'private_extensions/run_ugc_file_tools.py'), 'tool', args.tool]
    elif args.action == 'project-import':
        if not all((args.input, args.output, args.project)):
            raise ValueError('project-import requires --input, --output and --project')
        source, output = Path(args.input).resolve(), Path(args.output).resolve()
        if not source.is_file() or output.exists() or source == output:
            raise ValueError('Use an existing input and a new, different output file')
        command += [str(repo / 'private_extensions/run_ugc_file_tools.py'), 'project', 'import',
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
    p.add_argument('--repo', default=str(Path(__file__).resolve().parents[1] / 'vendor/ayaya'), help='Bundled tool root; optional explicit override')
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
