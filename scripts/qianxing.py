"""Unified Qianxing task routing, node discovery, input inventory and graph build CLI."""
from pathlib import Path
import argparse,json,subprocess,sys
from authoring_io import missing_input
from node_build import route,catalog,build
from level_inventory import inspect_file

DELEGATED = {
    'assets': ('asset_pipeline', 'Preview, generate, fit, inspect, or import assets'),
    'graph': ('graph_validation', 'Check one Graph Code source before building'),
    'workflow': ('qianxing_workflow', 'Select a development workflow'),
    'level': ('level_authoring', 'Create levels and bind client scripts'),
    'simulate': ('client_simulator', 'Check startup, preview UI, or run a scenario'),
    'native': ('native_core', 'Inspect, diff, plan, or apply native changes'),
    'storage': ('storage_authoring', 'Generate storage contracts'),
    'client': ('client_assembly', 'Assemble or check Lua'),
    'experiment': ('experiments', 'Run or compare experiments'),
    'verify': ('delivery_verify', 'Verify a delivery'),
    'docs': ('platform_profiles', 'Query platform documents'),
    'platform': ('platform_profiles', 'Check platform configuration'),
    'project': ('project_index', 'Search and inspect project objects and references'),
    'logs': ('log_diagnostics', 'Diagnose logs'),
    'ids': ('id_registry', 'Check registered IDs'),
    'ui': ('native_ui', 'Check or update native UI layout'),
    'resources': ('resource_catalogue', 'Find or verify resources'),
    'mcp': ('mcp_bridge', 'Run the local MCP service or make a fixed-operation call'),
    'beyond': ('beyond_backend', 'Run a Beyond software scenario'),
    'knowledge': ('knowledge', 'Query pinned API and documentation sources'),
    'diagnose': ('project_diagnosis', 'Run explicit read-only checks'),
    'scene': ('scene_authoring', 'Build static scenes and export native whitebox geometry'),
}

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    plan=sub.add_parser('plan');plan.add_argument('--kind',choices=['game','nodes','lua','gil','assets','animation','editor','diagnosis','storage','protocol'],default='game');plan.add_argument('--interface',choices=['lua','html','native','none'],default='lua');plan.add_argument('--multiplayer',action='store_true');plan.add_argument('--format',choices=['gia','gil','both','source'],default='gil')
    plan.add_argument('--task-mode',choices=['feature','fix','ui','assets','delivery'])
    plan.add_argument('--target-domain', choices=['editor','graph','client','gil','assets'], help='Object domain for shared diagnosis')
    find=sub.add_parser('nodes');find.add_argument('query',nargs='?',default='');find.add_argument('--scope',choices=['all','client','server'],default='all');find.add_argument('--limit',type=int,default=20)
    view=sub.add_parser('inspect');view.add_argument('input');view.add_argument('--out')
    make=sub.add_parser('build');make.add_argument('spec');make.add_argument('--out',required=True)
    production=sub.add_parser('produce');production.add_argument('spec');production.add_argument('--out',required=True)
    search=sub.add_parser('api');search.add_argument('query');search.add_argument('--limit',type=int,default=20)
    production.add_argument('--next',action='store_true',dest='next_output')
    production.add_argument('--summary',action='store_true')
    view.add_argument('--collection',action='store_true')
    for name, (_, description) in DELEGATED.items():
        sub.add_parser(name, help=description)
    doctor_parser=sub.add_parser('doctor');doctor_parser.add_argument('--compare',metavar='PLUGIN_ROOT')
    capability=sub.add_parser('capabilities');capability.add_argument('--evidence')
    capability.add_argument('--platform');capability.add_argument('--mode',choices=['classic','beyond'])
    try:
        if argv and argv[0] in DELEGATED:
            module, _ = DELEGATED[argv[0]]
            value = __import__(module).main(argv[1:])
            if isinstance(value, dict):
                print(json.dumps(value, ensure_ascii=False, indent=2))
                return 0
            return value
        a=p.parse_args(argv)
        if a.command in ('doctor','capabilities'):
            from capabilities import doctor,capabilities
            value=doctor(a.compare)if a.command=='doctor'else capabilities(a.evidence,platform=a.platform,mode=a.mode)
        elif a.command=='produce':
            from production_core import produce,produce_summary
            value=produce(a.spec,a.out,a.next_output)
            if a.summary:value=produce_summary(value)
        elif a.command=='api':
            from production_core import api
            value=api(a.query,a.limit)
        elif a.command=='plan':value=route(a.kind,a.interface,a.multiplayer,a.format,a.task_mode,a.target_domain)
        elif a.command=='nodes':value=catalog(a.query,a.scope,a.limit)
        elif a.command=='build':value=build(a.spec,a.out)
        else:
            path=Path(a.input)
            paths=sorted(path.glob('*.gil'))+sorted(path.glob('*.gia')) if path.is_dir() else [path]
            try:
                reports=[inspect_file(p) for p in paths]
            except FileNotFoundError as exc:
                raise missing_input(exc.filename or path, str(exc)) from exc
            value={'schema':'qianxing-inspect/v2','files':reports} if path.is_dir() or a.collection else {'schema':'qianxing-inspect/v2',**reports[0]}
            if a.out:
                with Path(a.out).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
        print(json.dumps(value,ensure_ascii=False,indent=2));return 2 if a.command=='doctor' and value['status']=='failed' else 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,ImportError,subprocess.SubprocessError) as exc:
        detail={}
        if hasattr(exc,'production_evidence'):detail['evidence']=exc.production_evidence
        if hasattr(exc,'diagnostics'):detail['diagnostics']=exc.diagnostics
        print(json.dumps({'error':str(exc),**detail},ensure_ascii=False) if detail else str(exc),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
