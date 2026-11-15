"""Isolated fixed-operation worker. stdout is never the MCP transport."""
from pathlib import Path
import contextlib,json,os,sys
from authoring_io import PLUGIN,sha,read_json,write_json


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
        if sha(Path(path).read_bytes())!=digest:raise ValueError('Worker input digest mismatch')
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
        elif op in('native_inspect','native_audit','project_inspect'):
            raw=Path(args['input']).read_bytes()
            if op=='project_inspect':
                from project_index import build
                result=build(raw)
            else:
                import native_core
                result=(native_core.inspect if op=='native_inspect'else native_core.audit)(raw)
        elif op=='client_check':
            from client_check import inspect
            result=inspect(args['input'],contract=read_json(args['contract'])if 'contract'in args else None)
        elif op=='native_diff':
            from native_changes import difference
            result=difference(Path(args['input']).read_bytes(),Path(args['other']).read_bytes())
        elif op=='native_plan':
            from native_changes import plan
            from authoring_io import output_directory,finish
            with output_directory(args['output'])as stage:
                result=plan(Path(args['input']).read_bytes(),read_json(args['spec']),Path(args['spec']).parent,stage)
                # Absolute project paths survive the private-stage directory commit.
                for item in result['inputs'].values():item['source']=str((stage/item['source']).resolve())
                write_json(stage/'plan.json',result)
                finish(stage,request['inputs'],kind='native-plan')
        elif op=='simulate':
            from joint_simulator import execute
            from authoring_io import output_directory,finish
            spec=read_json(args['spec'])
            if spec.get('schema')!=2:raise ValueError('MCP simulate requires schema 2')
            result=execute(spec,Path(args['spec']).parent)
            result['status']=result['acceptance']['status']
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
            result=verify(Path(args['input']).parent,args['rebuild'],args['portable'])
        elif op=='produce':
            from production_core import produce
            result=produce(args['spec'],args['output'])
        elif op=='native_apply':
            from native_changes import apply_plan
            from authoring_io import output_directory,finish
            raw,result=apply_plan(Path(args['input']).read_bytes(),read_json(args['plan']),Path(args['plan']).parent)
            with output_directory(args['output'])as stage:
                (stage/'level.gil').write_bytes(raw);write_json(stage/'native-report.json',result)
                finish(stage,request['inputs'],kind='native-apply')
        else:raise ValueError('Unknown worker operation')
    write_json(result_path,result)

if __name__=='__main__':main()
