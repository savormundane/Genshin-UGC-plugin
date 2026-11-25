"""Isolated fixed-operation worker. stdout is never the MCP transport."""
from pathlib import Path
import contextlib,json,os,sys
from authoring_io import DiagnosticError,PLUGIN,sha_file,read_json,write_json,resolve


def _asset_thumbnail(path, name, controls):
    from base64 import b64encode
    from io import BytesIO
    from PIL import Image

    with Image.open(path) as image, BytesIO() as thumbnail:
        image.thumbnail((256, 256), Image.Resampling.NEAREST)
        image.save(thumbnail, format='PNG')
        return {'name': name, 'controls': controls, 'data': b64encode(thumbnail.getvalue()).decode('ascii')}


def main():
    request=read_json(sys.argv[1]);result_path=Path(sys.argv[2]);args=request['arguments'];op=request['operation']
    scratch=Path(request['scratch']).resolve()
    project=Path(request['project']) if request['project'] else None
    mounted=[Path(request[k]).resolve() for k in ('project','output_root') if request[k]]
    roots=[scratch,PLUGIN.resolve(),Path(sys.base_prefix).resolve(),*mounted]
    roots.extend(Path(p).resolve() for p in sys.path if p and Path(p).is_dir()
                 and (project is None or not Path(p).resolve().is_relative_to(project)))
    native_cache=None
    if op=='produce':
        from beyond_native import native_cache_root
        cache=native_cache_root()
        if cache and cache.resolve()==cache and not any(
                cache.is_relative_to(owner) or owner.is_relative_to(cache) for owner in roots):
            native_cache=cache
    # A dependency boundary for trusted project builds, not an OS security sandbox.
    def boundary(event,values):
        if event not in('open','os.listdir','os.scandir'):return
        value=values[0]
        if value is None or isinstance(value,int):return
        path=Path(os.fsdecode(value)).resolve()
        if str(path).casefold()==os.devnull.casefold() or native_cache and path.is_relative_to(native_cache):return
        write=event=='open'and values[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
        if write and not path.is_relative_to(scratch):raise ValueError('MCP write outside request output')
        if not any(path.is_relative_to(r)for r in roots):raise ValueError('MCP dependency outside allowed roots')
    import tempfile
    tempfile.tempdir=str(scratch)
    sys.addaudithook(boundary)
    for path,digest in request['inputs'].items():
        actual=sha_file(path)
        if actual!=digest:
            raise DiagnosticError('mcp.input_sha256_mismatch','Worker input digest mismatch',phase=op,
                                  source=path,expected=digest,actual=actual)
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
        elif op=='graph_check':
            from graph_validation import check
            result=check(args['input'],args.get('bindings'),args.get('job'))
        elif op in('native_inspect','native_audit','project_inspect'):
            path=Path(args['input'])
            if op=='project_inspect':
                from project_index import build,consumers,inspect,inspect_summary,search
                if path.suffix.lower()=='.json' or 'scope'in args:
                    result=inspect(path,scope=args.get('scope'))
                else:
                    result=build(path.read_bytes())
                    result['inputs']={str(path):result['artifacts']['level']['sha256']}
                if 'query' in args:
                    result=search(result,args['query'],args.get('kind'),args.get('limit',20))
                elif 'selector' in args:
                    result=consumers(result,args['selector'],args.get('transitive',False))
                if args.get('summary'):result=inspect_summary(result)
            else:
                from miliastra.native import core as native_core
                result=(native_core.inspect if op=='native_inspect'else native_core.audit)(path.read_bytes())
        elif op=='client_check':
            from miliastra.client.check import inspect
            result=inspect(args['input'],mapping=args.get('mapping'),contract=read_json(args['contract'])if 'contract'in args else None)
        elif op=='native_diff':
            from miliastra.native.changes import difference
            result=difference(Path(args['input']).read_bytes(),Path(args['other']).read_bytes(),args.get('allowed_top_level_fields'))
        elif op == 'scene_preview':
            from scene_preview import preview
            result = preview(args['input'], args['output'], before=args.get('before'))
        elif op == 'asset_preview':
            from miliastra.assets.pipeline import preview
            output = Path(args['output'])
            try:
                result = preview(args['input'], output, image_format='PNG', explore=True,
                                 max_controls=args.get('max_controls'), step=args.get('step', 1))
            except (OSError, ValueError) as exc:
                raise DiagnosticError('asset.preview_invalid', str(exc), phase=op, source=args['input']) from exc
            original, *alternatives = result['candidates']
            selected = [original]
            if alternatives:
                visible = [candidate for candidate in alternatives if candidate['controls']]
                selected.append(min(visible or alternatives, key=lambda candidate: (
                    candidate['within_budget'] is False, candidate['controls'], candidate['error'])))
            result['_inline_previews'] = [
                _asset_thumbnail(output / candidate['display_preview'], candidate['name'], candidate['controls'])
                for candidate in selected
            ]
        elif op == 'asset_generate':
            from miliastra.assets.pipeline import generate
            try:
                result = generate(args['input'], args['output'], from_preview=args['report'], candidate=args['candidate'])
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise DiagnosticError(
                    'asset.generate_invalid', '素材生成失败。请核对源图对应的试算报告、候选名称和预算后重试。',
                    phase=op, source=args['input'], report=args['report'], candidate=args['candidate'], detail=str(exc),
                ) from exc
            result['_inline_previews'] = [
                _asset_thumbnail(Path(args['output']) / 'preview.png', args['candidate'], result['controls'])
            ]
        elif op=='native_plan':
            from miliastra.native.changes import plan,plan_summary
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
            if args.get('summary'):result=plan_summary(result)
        elif op=='simulate':
            from joint_simulator import evaluate,load_scenario
            from authoring_io import output_directory,finish
            spec,base,inputs=load_scenario(args['spec'])
            result=evaluate(spec,base,expected_inputs=inputs)
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
            result=verify(Path(args['input']).parent,args.get('rebuild',False),args.get('portable',False),
                          args.get('trusted_inputs_sha256'),artifacts_only=args.get('artifacts_only',False))
        elif op=='produce':
            from production_core import produce,produce_summary,ProductionError
            try:
                result=produce(args['spec'],args['output'])
                if args.get('summary'):result=produce_summary(result)
            except ProductionError as exc:
                result={'status':'failed','error':str(exc),'evidence':exc.production_evidence,
                        'diagnostics':getattr(exc,'diagnostics',[])}
        elif op=='native_apply':
            from miliastra.native.changes import apply_plan
            from authoring_io import output_directory,finish
            raw,result=apply_plan(Path(args['input']).read_bytes(),read_json(args['plan']),Path(args['plan']).parent)
            with output_directory(args['output'])as stage:
                (stage/'level.gil').write_bytes(raw);write_json(stage/'native-report.json',result)
                if 'layout_bindings' in result:write_json(stage/'layout-bindings.json',result['layout_bindings'])
                finish(stage,{**request['inputs'],**result['inputs']},kind='native-apply')
        else:raise ValueError('Unknown worker operation')
    write_json(result_path,result)

if __name__=='__main__':
    try:
        main()
    except DiagnosticError as exc:
        write_json(sys.argv[2],{'status':'failed','error':str(exc),'diagnostics':exc.diagnostics})
