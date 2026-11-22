"""Optional pinned external simulator; explicit project and final-source bindings."""
from pathlib import Path
import argparse,json,subprocess,tempfile,shutil
from authoring_io import read_json,sha,schema,resolve,output_directory,write_json,finish
PIN='02a5ea2cd38bb5bcf7a7ce6dd745be3bb1ae655c'
BUNDLED=Path(__file__).resolve().parent.parent/'vendor/beyond'
# npm-compatible Git installations omit these upstream ignore rules.
NON_RUNTIME_GITIGNORE={'dsh-plugin/.gitignore','client/lua-runtime/.gitignore',
                       'node_modules/qxqy-lua-runtime/.gitignore'}
def run(path,backend,out,*,final_gil=None,preview=False):
    path=Path(path).resolve();backend=Path(backend or BUNDLED).resolve()
    spec_bytes=path.read_bytes()
    spec=json.loads(spec_bytes.decode('utf-8-sig'))
    schema(spec,('schema','project','gil','scripts','case','render','render_checks'),('scripts','case'))
    if ('project'in spec)==('gil'in spec):raise ValueError('Choose project or gil')
    if not isinstance(spec['scripts'],list)or not spec['scripts']:raise ValueError('Explicit scripts required')
    bound=[]
    for item in ([spec['gil']] if 'gil'in spec else [])+spec['scripts']:
        if item.get('source')=='@level':
            if final_gil is None or not Path(final_gil).is_file():raise ValueError('@level requires the current production final GIL')
            final_gil=Path(final_gil).resolve();digest=sha(final_gil.read_bytes())
            if item.get('sha256') not in ('@level',digest):raise ValueError('Final GIL digest differs from declared binding')
            item['source']=str(final_gil);item['sha256']=digest
            bound.append({'source':'level.gil','sha256':digest,'mapping':item.get('mapping'),'control_guid':item.get('control_guid',item.get('root_guid'))})
        elif item.get('sha256')=='@level':raise ValueError('@level digest requires @level source')
    if type(spec.get('render',False)) is not bool:raise ValueError('render must be boolean')
    if preview:spec['render']=True
    if 'render_checks'in spec:
        if not spec.get('render') or not isinstance(spec['render_checks'],list) or not spec['render_checks']:raise ValueError('Render checks require rendering and a nonempty list')
        for check in spec['render_checks']:
            schema(check,('name','width','height','text'),('name',))
            if not isinstance(check['name'],str) or not check['name'] or len(check)==1:raise ValueError('Named render expectation required')
    if Path(out).exists():raise ValueError('Output exists; use a new directory')
    bundle=backend/'bundle.json'
    if bundle.is_file():
        manifest=read_json(bundle);revision=manifest['commit']
        for name,digest in manifest['files'].items():
            target=(backend/name).resolve()
            if name in NON_RUNTIME_GITIGNORE and not target.exists():continue
            if not target.is_relative_to(backend) or not target.is_file() or sha(target.read_bytes())!=digest:raise ValueError('Bundled backend integrity failure: '+name)
    else:
        revision=subprocess.run(['git','-C',str(backend),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
        dirty=subprocess.run(['git','-C',str(backend),'status','--porcelain','--untracked-files=no'],capture_output=True,text=True,check=True).stdout
        if dirty:raise ValueError('Modified backend source refused')
    if revision!=PIN:raise ValueError('Unsupported backend commit')
    if not isinstance(spec['case'],dict):raise ValueError('Beyond case must be an object')
    if not preview and not spec['case'].get('asserts'):raise ValueError('Nonempty assertions required')
    inputs={str(path):sha(spec_bytes)};scripts=[]
    gil=None;project_data=None
    if 'gil'in spec:
        from beyond_gil import convert
        source=resolve(path.parent,spec['gil']['source']);raw=source.read_bytes();inputs[str(source)]=sha(raw)
        gil=convert(raw,spec['gil'])
    else:
        project=resolve(path.parent,spec['project']);raw=project.read_bytes();inputs[str(project)]=sha(raw)
        project_data=json.loads(raw.decode('utf-8-sig'))
    mounted=set()
    for item in spec['scripts']:
        schema(item,('source','sha256','mapping','controlId','controlAsset','control_guid','path'),('source','sha256','path'))
        source=resolve(path.parent,item['source']);raw=source.read_bytes()
        if sha(raw)!=item['sha256']:raise ValueError('Final source digest mismatch')
        inputs[str(source)]=sha(raw)
        if source.suffix.lower()=='.gil':
            from joint_simulator import script_from_gil
            if not item.get('mapping'):raise ValueError('Exact GIL mapping required')
            code,_=script_from_gil(raw,item['mapping'])
        else:code=raw.decode('utf-8-sig')
        if gil:
            if source!=resolve(path.parent,spec['gil']['source']):raise ValueError('GIL UI and scripts must share final source')
            matches=[s for s in gil['scripts'] if s['name']==item.get('mapping')]
            pair=(item.get('control_guid'),matches[0]['id'] if len(matches)==1 else None)
            if pair in mounted or not any((b['control_guid'],b['script_guid'])==pair for b in gil['bindings']):raise ValueError('Script mount differs from GIL')
            mounted.add(pair);scripts.append({'control_guid':pair[0],'path':item['path'],'source':code})
        else:scripts.append({k:item[k]for k in ('controlId','controlAsset','path')}|{'source':code})
    if gil and mounted!={(b['control_guid'],b['script_guid']) for b in gil['bindings']}:raise ValueError('Every selected native script mount must be supplied')
    if bundle.is_file():inputs[str(bundle)]=sha(bundle.read_bytes())
    # Refuse hidden embedded scripts: every executed source must be digest-bound.
    def embedded(v):
        if isinstance(v,dict):
            if v.get('scripts'):raise ValueError('Project must not contain unbound scripts')
            for x in v.values():embedded(x)
        elif isinstance(v,list):
            for x in v:embedded(x)
    embedded(project_data)
    node=shutil.which('node')
    if not node:raise ValueError('Node 22+ required')
    if int(subprocess.check_output([node,'--version'],text=True).strip().lstrip('v').split('.')[0])<22:raise ValueError('Node 22+ required')
    with tempfile.TemporaryDirectory(prefix='ugc-beyond-')as td:
        td=Path(td);write_json(td/'job.json',{'entry':str(backend/'studio/index.js'),'project':project_data,'gil':gil,'scripts':scripts,'case':spec['case'],'render':spec.get('render',False),'render_checks':spec.get('render_checks',[])})
        proc=subprocess.run([node,str(Path(__file__).with_name('beyond_worker.mjs')),str(td/'job.json'),str(td/'result.json')],capture_output=True,text=True,encoding='utf-8',timeout=45)
        if proc.returncode:raise ValueError('External simulator failed: '+proc.stderr[-3000:])
        result=read_json(td/'result.json')
        passed=result.get('passed') is True
        if not preview and (not passed or result['checks']['assertions']['executed']==0):
            raise ValueError('External assertions failed: '+json.dumps(result,ensure_ascii=False))
        status='passed' if passed else 'failed'
        destination=Path(out).resolve()
        if not passed:destination=destination.with_name(destination.name+'.diagnostics')
        report={'status':status,'backend_commit':revision,'final_gil_bindings':bound,'layer':'external_lua_model',
                'report':result,'checks':result['checks'],'diagnostics':result['diagnostics'],'logs':result['logs'],
                'editor':'not_checked','host':'not_checked',
                'rendering':result['checks']['render_assertions']['status'],
                'preview_generated':result['checks']['preview']['generated'],'render_layer':'software_preview',
                'native_graph_model':'not_applicable',
                'template_identity':'selected_native_guid_bindings' if gil else 'explicit_project_binding_not_native_equivalence'}
        if not passed and destination.exists():
            report['diagnostics'].append({'code':'diagnostics_output_exists',
                                          'message':'Diagnostics path already exists. Choose a new --out path.',
                                          'path':str(destination)})
            return {**report,'inputs':inputs,'output':None,'diagnostics_output':None}
        with output_directory(destination)as stage:
            for name in ('preview.png','render.json','converted-project.json'):
                if (td/name).is_file():shutil.copy2(td/name,stage/name)
            write_json(stage/'external-simulation.json',report)
            manifest=finish(stage,inputs,kind='external-simulation',status=status,backend_commit=revision)
        if preview:
            return {**report,'inputs':inputs,'output':str(destination) if passed else None,
                    'diagnostics_output':str(destination) if not passed else None}
        return manifest
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('spec');p.add_argument('--backend');p.add_argument('--out',required=True);a=p.parse_args(argv)
    print(json.dumps(run(a.spec,a.backend,a.out),ensure_ascii=False));return 0
