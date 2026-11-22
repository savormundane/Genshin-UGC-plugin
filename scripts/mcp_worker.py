"""Isolated fixed-operation worker. stdout is never the MCP transport."""
from pathlib import Path
import contextlib,json,os,sys
from authoring_io import PLUGIN,sha_file,read_json,write_json,resolve


def main():
    request=read_json(sys.argv[1]);result_path=Path(sys.argv[2]);args=request['arguments'];op=request['operation']
    roots=[Path(request[k]).resolve()for k in('project','output_root')]+[PLUGIN.resolve(),Path(sys.base_prefix).resolve()]
    roots.extend(Path(p).resolve()for p in sys.path if p and Path(p).is_dir()and not Path(p).resolve().is_relative_to(Path(request['project'])))
    scratch=Path(request['scratch']).resolve()
    # A dependency boundary for trusted project builds, not an OS security sandbox.
    def boundary(event,values):
        if event not in('open','os.listdir','os.scandir'):return
        value=values[0]
        if value is None or isinstance(value,int):return
        path=Path(os.fsdecode(value)).resolve()
        if str(path).casefold()==os.devnull.casefold():return
        write=event=='open'and values[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
        if write and not path.is_relative_to(scratch):raise ValueError('MCP write outside request output')
        if not any(path.is_relative_to(r)for r in roots):raise ValueError('MCP dependency outside allowed roots')
    import tempfile
    tempfile.tempdir=str(scratch)
    sys.addaudithook(boundary)
    for path,digest in request['inputs'].items():
        if sha_file(path)!=digest:raise ValueError('Worker input digest mismatch')
    with contextlib.redirect_stdout(sys.stderr):
        if op in('doctor','capabilities'):
            import capabilities
            result=getattr(capabilities,op)()
        elif op=='api_lookup':
            from knowledge import api
            result=api(args['symbol'])
        elif op=='diagnose':
            from project_diagnosis import diagnose
            result=diagnose(args['spec'])
        elif op=='docs_search':
            from platform_profiles import search
            result={'status':'passed','matches':search(args['version'],args['query'])}
        elif op=='resources_lookup':
            from resource_catalogue import search
            result=search(args['version'],args.get('query',''),'model',args.get('mode','beyond'),
                          [args['catalogue']] if 'catalogue' in args else (),args.get('limit',20))
        elif op=='nodes_lookup':
            from node_build import catalog
            result=catalog(**args)
        elif op in('native_inspect','native_audit','project_inspect'):
            path=Path(args['input'])
            if op=='project_inspect':
                from project_index import build,consumers,inspect
                if path.suffix.lower()=='.json':
                    result=inspect(path)
                else:
                    result=build(path.read_bytes())
                    result['inputs']={str(path):result['artifacts']['level']['sha256']}
                if 'selector' in args:
                    result=consumers(result,args['selector'],args.get('transitive',False))
            else:
                import native_core
                result=(native_core.inspect if op=='native_inspect'else native_core.audit)(path.read_bytes())
        elif op=='client_check':
            from client_check import inspect
            result=inspect(args['input'],mapping=args.get('mapping'),contract=read_json(args['contract'])if 'contract'in args else None)
        elif op=='native_diff':
            from native_changes import difference
            result=difference(Path(args['input']).read_bytes(),Path(args['other']).read_bytes(),args.get('allowed_top_level_fields'))
        elif op=='native_plan':
            from native_changes import plan
            from authoring_io import output_directory,finish
            if 'patch' in args:
                patch=args['patch']
                base=Path(request['project'])
            else:
                source=Path(args['spec'])
                patch=read_json(source)
                base=source.parent
            with output_directory(args['output'])as stage:
                result=plan(Path(args['input']).read_bytes(),patch,base,stage)
                # Absolute project paths survive the private-stage directory commit.
                inputs=dict(request['inputs'])
                for item in result['inputs'].values():
                    item['source']=str(resolve(stage,item['source']))
                    inputs[item['source']]=item['sha256']
                write_json(stage/'plan.json',result)
                finish(stage,inputs,kind='native-plan')
        elif op=='simulate':
            from joint_simulator import evaluate
            from authoring_io import output_directory,finish
            spec=read_json(args['spec'])
            result=evaluate(spec,Path(args['spec']).parent)
            if result['status']=='passed':
                with output_directory(args['output'])as stage:
                    write_json(stage/'simulation.json',result)
                    finish(stage,{**request['inputs'],**result['inputs']},kind='simulation')
        elif op=='experiment_run':
            from experiments import build
            result=build(args['spec'],args['output'])
        elif op=='experiment_compare':
            from experiments import compare
            result=compare(read_json(args['input']),read_json(args['other']))
        elif op=='logs_diagnose':
            from log_diagnostics import diagnose
            result=diagnose(args['spec'])
        elif op=='verify':
            from delivery_verify import verify
            if Path(args['input']).name!='manifest.json':raise ValueError('Verification input must be manifest.json')
            result=verify(Path(args['input']).parent,args['rebuild'],args['portable'],args.get('trusted_inputs_sha256'))
        elif op=='produce':
            from production_core import produce,ProductionError
            try:
                result=produce(args['spec'],args['output'])
            except ProductionError as exc:
                result={'status':'failed','error':str(exc),'evidence':exc.production_evidence,
                        'diagnostics':getattr(exc,'diagnostics',[])}
        elif op=='native_apply':
            from native_changes import apply_plan
            from authoring_io import output_directory,finish
            raw,result=apply_plan(Path(args['input']).read_bytes(),read_json(args['plan']),Path(args['plan']).parent)
            with output_directory(args['output'])as stage:
                (stage/'level.gil').write_bytes(raw);write_json(stage/'native-report.json',result)
                finish(stage,{**request['inputs'],**result['inputs']},kind='native-apply')
        else:raise ValueError('Unknown worker operation')
    write_json(result_path,result)

if __name__=='__main__':main()
