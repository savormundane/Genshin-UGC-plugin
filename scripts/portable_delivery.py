"""Explicit input closure, immutable originals and isolated portable production."""
from pathlib import Path
import importlib.util,json,os,re,shutil,subprocess,sys,tempfile
from authoring_io import PLUGIN,read_json,sha,inventory,write_json,output_directory,finish,schema
from validation_evidence import backend_inventory

def collect(path,options):
    path=Path(path).resolve();base=path.parent
    schema(options,('roots','dependencies'))
    roots={'project':base,'toolchain':PLUGIN}
    for name,value in options.get('roots',{}).items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',name)or name in roots:raise ValueError('Unique portable root name required')
        roots[name]=(base/value).resolve()
    files={};configs={};bindings=[];directories={}
    def add(source):
        source=Path(os.path.abspath(source))
        owners=[(name,root)for name,root in roots.items()if source.is_relative_to(root)]
        if not owners:raise ValueError('Input outside declared portable roots: '+str(source))
        name,root=max(owners,key=lambda item:len(item[1].parts))
        if any(p.is_symlink()for p in (source,*source.parents)if p.is_relative_to(root)):
            raise ValueError('Linked portable input: '+str(source))
        if source.is_dir():
            listing=inventory(source);directories[source]=(name+'/'+source.relative_to(root).as_posix(),listing)
            for relative in listing:add(source/relative)
        elif source.is_file():files[source]=name+'/'+source.relative_to(root).as_posix()
        else:raise ValueError('Portable input missing: '+str(source))
        return source
    def reference(config,container,key,kind=None):
        value=container[key]
        if value=='@level'or value.startswith('@asset:'):return
        raw=config.parent/value
        target=add(raw);bindings.append((config,container,key,target))
        if kind:visit(target,kind)
    def visit(source,kind):
        source=add(source)
        if source in configs:
            if configs[source][0]!=kind:raise ValueError('Ambiguous configuration role: '+str(source))
            return
        value=read_json(source);configs[source]=(kind,value)
        if kind=='job':
            value.pop('portable',None)
            if 'client'in value:
                c=value['client'];reference(source,c,'assembly'if 'assembly'in c else'source','assembly'if 'assembly'in c else None)
            if 'backend'in value.get('beyond',{}):raise ValueError('Portable Beyond requires the bundled backend; omit backend')
            for key in('level','storage','graphs','simulation','experiment','platform','project','client_check','ui','resources','beyond'):
                if key in value:reference(source,value[key],'spec',key)
            for key in('native','storage','gil'):
                if key in value:
                    for field in('base','source'):
                        if field in value[key]:reference(source,value[key],field)
            if 'native'in value:
                native=value['native'];reference(source,native,'plan'if 'plan'in native else'spec','native_plan'if 'plan'in native else'native')
            for item in value.get('assets',[]):
                reference(source,item,'source')
                if 'spec'in item:reference(source,item,'spec')
            for item in value.get('animation',{}).get('frames',[]):reference(source,item,'asset')
        elif kind in('assembly','level','graphs'):
            key={'assembly':'sources','level':'scripts','graphs':'graphs'}[kind]
            for item in value[key]:
                if 'source'in item:reference(source,item,'source')
            if kind=='graphs':
                for key in('base_gil','project_resources'):
                    if value.get(key):reference(source,value,key)
        elif kind=='native':
            for item in value['operations']:
                if 'source'in item:reference(source,item,'source')
        elif kind=='native_plan':
            for item in value['inputs'].values():reference(source,item,'source')
        elif kind=='simulation':
            for item in value['clients']+([value['server']]if value.get('server')else[]):reference(source,item,'source')
        elif kind=='experiment':reference(source,value,'source')
        elif kind=='beyond':
            if 'project'in value:reference(source,value,'project')
            if 'gil'in value:reference(source,value['gil'],'source')
            for item in value['scripts']:reference(source,item,'source')
        elif kind=='project':
            for item in value['artifacts']:reference(source,item,'source')
        elif kind=='resources':
            for i in range(len(value.get('catalogues',[]))):reference(source,value['catalogues'],i,'resource_catalogue')
        elif kind=='resource_catalogue':
            for item in value['resources']:reference(source,item['source'],'path')
    visit(path,'job')
    for item in options.get('dependencies',[]):
        raw=base/item
        add(raw)
    # Include the complete independent plugin, including calibrations, official
    # rules, backend definitions and licenses; omit only inventory's cache files.
    add(PLUGIN)
    return path,roots,files,configs,bindings,directories

def execute(bundle,out):
    bundle=Path(bundle).resolve();out=Path(out).resolve();record=read_json(bundle/'portable.json')
    if record.get('schema')!=1:raise ValueError('Unknown portable delivery schema')
    if backend_inventory()!=record['backends']:raise ValueError('Portable execution backend differs from recorded dependencies')
    work=bundle/'workspace'
    with tempfile.TemporaryDirectory(prefix='qianxing-portable-run-')as temporary:
        scratch=Path(temporary);trace=scratch/'trace';trace.mkdir()
        read_roots=[str(work),str(out.parent),str(scratch),str(Path(sys.base_prefix).resolve()),str(Path(sys.prefix).resolve())]
        package_paths=[]
        for name in('lupa','PIL'):
            spec=importlib.util.find_spec(name)
            if spec and spec.submodule_search_locations:
                read_roots.extend(spec.submodule_search_locations)
                package_paths.extend(str(Path(p).parent)for p in spec.submodule_search_locations)
        boundary={'read_roots':read_roots,'write_roots':[str(out.parent),str(scratch)],'trace':str(trace)}
        runner=work/'toolchain/scripts/dependency_runner.py'
        command=[sys.executable,'-X','utf8','-B',str(runner),str(work/'toolchain/scripts/qianxing.py'),'produce',str(work/record['job']),'--out',str(out)]
        env={**os.environ,'UGC_BUILD_BOUNDARY':json.dumps(boundary),'TMP':str(scratch),'TEMP':str(scratch),'TMPDIR':str(scratch),'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':os.pathsep.join(dict.fromkeys(package_paths))}
        process=subprocess.run(command,cwd=work,env=env,capture_output=True,text=True,encoding='utf-8',timeout=900)
        if process.returncode:raise ValueError('Portable build failed: '+(process.stdout+process.stderr)[-18000:])
        traces=list(trace.glob('*.json'));reads=sorted({name for path in traces for name in read_json(path)})
        return {'status':'passed','python_processes':len(traces),'python_read_files':len(reads),'scope':'trusted Python producers and compiler children; external runtime dependencies fingerprinted','editor':'not_checked','host':'not_checked'}

def produce(path,out,evidence):
    job=read_json(path);path,roots,files,configs,bindings,directories=collect(path,job['portable'])
    original={str(p):sha(p.read_bytes())for p in files};backends=backend_inventory()
    with output_directory(out)as stage:
        bundle=stage/'portable';work=bundle/'workspace';raw=bundle/'original'
        for relative,_ in directories.values():(work/relative).mkdir(parents=True,exist_ok=True)
        for source,relative in files.items():
            target=work/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
            if not relative.startswith('toolchain/'):
                saved=raw/relative;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,saved)
        relocations=[]
        for config,container,key,target in bindings:
            # Directories have no entry in files: derive their root ownership.
            name,root=max(((n,r)for n,r in roots.items()if target.is_relative_to(r)),key=lambda item:len(item[1].parts))
            relative=name+'/'+target.relative_to(root).as_posix()
            value=Path(os.path.relpath(work/relative,(work/files[config]).parent)).as_posix()
            relocations.append({'configuration':files[config],'field':key,'original':container[key],'relocated':value})
            container[key]=value
        for source,(_,value)in configs.items():write_json(work/files[source],value)
        write_json(bundle/'portable.json',{'schema':1,'job':files[path],'backends':backends,'original_inputs':original,'relocations':relocations,'files':inventory(bundle)})
        snapshot=inventory(bundle)
        with tempfile.TemporaryDirectory(prefix='qianxing-portable-output-',dir=stage.parent)as directory:
            result=Path(directory)/'result';execution=execute(bundle,result)
            inner=read_json(result/'manifest.json')
            for item in result.iterdir():shutil.move(str(item),str(stage/item.name))
        if snapshot!=inventory(bundle):raise ValueError('Portable input snapshot changed during production')
        if any(inventory(source)!=listing for source,(_,listing)in directories.items()):raise ValueError('Portable input directory changed during production')
        evidence.update(inner['evidence']);evidence['portable_inputs']={'status':'passed','report':'portable/portable.json'}
        if backend_inventory()!=backends:raise ValueError('Execution backend changed during portable production')
        from delivery_artifacts import roles
        report=finish(stage,original,kind='production',specification=str(path),stages=inner['stages'],evidence=evidence,portable={'schema':1,'root':'portable','execution':execution})
        write_json(stage/'production-report.json',report)
        report['files']={name:digest for name,digest in inventory(stage).items()if name!='manifest.json'}
        report['artifacts']=roles(report['files']);write_json(stage/'manifest.json',report)
    return report
