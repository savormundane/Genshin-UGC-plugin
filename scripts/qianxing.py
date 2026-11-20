"""Unified Qianxing task routing, node discovery, input inventory and graph build CLI."""
from pathlib import Path
import argparse,json,subprocess,sys
from node_build import route,catalog,build
from level_inventory import inspect_file

def main(argv=None):
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    plan=sub.add_parser('plan');plan.add_argument('--kind',choices=['game','nodes','lua','gil','assets','animation','editor','diagnosis','storage','protocol'],default='game');plan.add_argument('--interface',choices=['lua','html','native','none'],default='lua');plan.add_argument('--multiplayer',action='store_true');plan.add_argument('--format',choices=['gia','gil','both','source'],default='gil')
    plan.add_argument('--task-mode',choices=['feature','fix','ui','assets','delivery'])
    plan.add_argument('--target-domain', choices=['editor','graph','client','gil','assets'], help='Object domain for shared diagnosis')
    find=sub.add_parser('nodes');find.add_argument('query',nargs='?',default='');find.add_argument('--scope',choices=['all','client','server'],default='all');find.add_argument('--limit',type=int,default=20)
    view=sub.add_parser('inspect');view.add_argument('input');view.add_argument('--out')
    make=sub.add_parser('build');make.add_argument('spec');make.add_argument('--out',required=True)
    asset=sub.add_parser('assets');asset.add_argument('args',nargs=argparse.REMAINDER)
    production=sub.add_parser('produce');production.add_argument('spec');production.add_argument('--out',required=True)
    search=sub.add_parser('api');search.add_argument('query');search.add_argument('--limit',type=int,default=20)
    workflow=sub.add_parser('workflow');workflow.add_argument('args',nargs=argparse.REMAINDER)
    production.add_argument('--next',action='store_true',dest='next_output')
    view.add_argument('--collection',action='store_true')
    native=sub.add_parser('level');native.add_argument('args',nargs=argparse.REMAINDER)
    simulation=sub.add_parser('simulate');simulation.add_argument('args',nargs=argparse.REMAINDER)
    for name in ('native','storage','client','experiment','verify','docs','platform','project','logs','ids','ui','resources','mcp','beyond','knowledge','diagnose'):
        command=sub.add_parser(name);command.add_argument('args',nargs=argparse.REMAINDER)
    sub.add_parser('doctor')
    capability=sub.add_parser('capabilities');capability.add_argument('--evidence')
    capability.add_argument('--platform');capability.add_argument('--mode',choices=['classic','beyond'])
    a=p.parse_args(argv)
    try:
        if a.command in ('workflow', 'assets'):
            module = 'qianxing_workflow' if a.command == 'workflow' else 'asset_pipeline'
            return __import__(module).main(a.args)
        if a.command in ('knowledge','diagnose'):
            return __import__('knowledge' if a.command=='knowledge' else 'project_diagnosis').main(a.args)
        if a.command in ('native','storage','client','experiment','verify','docs','platform','project','logs','ids','ui','resources','mcp','beyond'):
            module={'native':'native_core','storage':'storage_authoring','client':'client_assembly','experiment':'experiments','verify':'delivery_verify','docs':'platform_profiles','platform':'platform_profiles','project':'project_index','logs':'log_diagnostics','ids':'id_registry','ui':'native_ui','resources':'resource_catalogue','mcp':'mcp_bridge','beyond':'beyond_backend'}[a.command]
            return __import__(module).main(a.args)
        if a.command in ('doctor','capabilities'):
            from capabilities import doctor,capabilities
            value=doctor()if a.command=='doctor'else capabilities(a.evidence,platform=a.platform,mode=a.mode)
        elif a.command=='level':
            from level_authoring import main as level_main
            value=level_main(a.args)
        elif a.command=='simulate':
            from client_simulator import main as simulate_main
            value=simulate_main(a.args)
        elif a.command=='produce':
            from production_core import produce
            value=produce(a.spec,a.out,a.next_output)
        elif a.command=='api':
            from production_core import api
            value=api(a.query,a.limit)
        elif a.command=='plan':value=route(a.kind,a.interface,a.multiplayer,a.format,a.task_mode,a.target_domain)
        elif a.command=='nodes':value=catalog(a.query,a.scope,a.limit)
        elif a.command=='build':value=build(a.spec,a.out)
        else:
            path=Path(a.input)
            paths=sorted(path.glob('*.gil'))+sorted(path.glob('*.gia')) if path.is_dir() else [path]
            reports=[inspect_file(p) for p in paths]
            value={'schema':'qianxing-inspect/v2','files':reports} if path.is_dir() or a.collection else {'schema':'qianxing-inspect/v2',**reports[0]}
            if a.out:
                with Path(a.out).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
        print(json.dumps(value,ensure_ascii=False,indent=2));return 2 if a.command=='doctor' and value['status']=='failed' else 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError,ImportError,subprocess.SubprocessError) as exc:
        print(json.dumps({'error':str(exc),'evidence':exc.production_evidence},ensure_ascii=False) if hasattr(exc,'production_evidence') else str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
