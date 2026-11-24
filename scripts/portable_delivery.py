"""Explicit input closure, immutable originals and isolated portable production."""
from pathlib import Path
import importlib.util,json,os,re,shutil,subprocess,sys,tempfile
from authoring_io import PLUGIN,ProductionInputs,read_json,sha,inventory,write_json,output_directory,finish,schema
from validation_evidence import backend_inventory


def unbundled_canvas_lock(job, backend):
    if 'beyond' not in job:
        return None
    from beyond_native import read_native_lock, verify_native_files
    lock = read_native_lock(backend)
    return lock if lock is not None and not verify_native_files(backend, lock) else None


def copy_canvas_payload(source, destination, lock):
    from beyond_native import verify_native_files
    if not verify_native_files(source, lock):
        raise ValueError('Portable Beyond Canvas input missing')
    for name in lock['files']:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    verify_native_files(destination, lock)


def collect(path,options,*,snapshot_root=None,inputs=None):
    path=Path(path).resolve();base=path.parent
    schema(options,('roots','dependencies'))
    roots={'project':base,'toolchain':PLUGIN}
    if snapshot_root is not None:
        roots={p.name:p for p in Path(snapshot_root).iterdir() if p.is_dir() and p.name!='toolchain'}
    for name,value in options.get('roots',{}).items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',name)or name in roots:raise ValueError('Unique portable root name required')
        roots[name]=(base/value).resolve()
    files={};configs={};bindings=[];directories={}
    def add(source,digest=None):
        source=Path(os.path.abspath(source))
        owners=[(name,root)for name,root in roots.items()if source.is_relative_to(root)]
        if not owners:raise ValueError('Input outside declared portable roots: '+str(source))
        name,root=max(owners,key=lambda item:len(item[1].parts))
        if any(p.is_symlink()for p in (source,*source.parents)if p.is_relative_to(root)):
            raise ValueError('Linked portable input: '+str(source))
        if source.is_dir():
            listing=inventory(source);directories[source]=(name+'/'+source.relative_to(root).as_posix(),listing)
            for relative,bound_digest in listing.items():add(source/relative,bound_digest)
        elif source.is_file():
            files[source]=name+'/'+source.relative_to(root).as_posix()
            if inputs is not None:
                if digest is None:inputs.track(source,'portable_collection')
                else:inputs.bind(source,digest,'portable_collection')
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
        raw=source.read_bytes()
        if inputs is not None:inputs.bind(source,sha(raw),'portable_configuration')
        value=json.loads(raw.decode('utf-8-sig'));configs[source]=(kind,value)
        if kind=='job':
            if value.get('schema')!=2:raise ValueError('Portable job requires schema 2')
            value.pop('portable',None)
            if 'client'in value:
                c=value['client'];reference(source,c,'assembly'if 'assembly'in c else'source','assembly'if 'assembly'in c else None)
            if 'backend'in value.get('beyond',{}):raise ValueError('Portable Beyond requires the bundled backend; omit backend')
            for key in('level','storage','graphs','simulation','experiment','platform','project','client_check','ui','resources','beyond'):
                if key in value:reference(source,value[key],'spec',key)
            if 'scene'in value:
                scene=value['scene']
                if 'spec'in scene:reference(source,scene,'spec','scene')
                if 'whitebox'in scene:reference(source,scene['whitebox'],'source')
            for key in('native','storage','gil'):
                if key in value:
                    for field in('base','source'):
                        if field in value[key]:reference(source,value[key],field)
            if 'native'in value:
                native=value['native'];reference(source,native,'plan'if 'plan'in native else'spec','native_plan'if 'plan'in native else'native')
                if 'after_graphs'in native:reference(source,native,'after_graphs','native')
            for item in value.get('assets',[]):
                source_kind='asset_batch' if item.get('kind')=='batch' else 'fit_layers' if item.get('kind')=='fit' and Path(item['source']).suffix.lower()=='.json' else None
                reference(source,item,'source',source_kind)
                if 'spec'in item:reference(source,item,'spec')
            for item in value.get('animation',{}).get('frames',[]):reference(source,item,'asset')
        elif kind in('assembly','level','graphs'):
            key={'assembly':'sources','level':'scripts','graphs':'graphs'}[kind]
            for item in value[key]:
                if 'source'in item:reference(source,item,'source')
            if kind=='graphs':
                for key in('base_gil','project_resources','bindings'):
                    if value.get(key):reference(source,value,key)
        elif kind=='fit_layers':
            for layer in value['layers']:reference(source,layer,'source')
        elif kind=='asset_batch':
            for item in value['assets']:reference(source,item,'source')
        elif kind=='native':
            from native_changes import operation_sources
            for item in value['operations']:
                for field in operation_sources(item):
                    if field=='source' and item.get('op')=='place_static_scene' and item[field]=='@scene':continue
                    reference(source,item,field)
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
        elif kind in ('resources', 'scene'):
            for i in range(len(value.get('catalogues',[]))):reference(source,value['catalogues'],i,'resource_catalogue')
        elif kind=='resource_catalogue':
            for item in value['resources']:
                reference(source,item['source'],'path')
                if 'dimensions_source' in item:reference(source,item['dimensions_source'],'path')
    visit(path,'job')
    for item in options.get('dependencies',[]):
        raw=base/item
        add(raw)
    # Include the complete independent plugin, including calibrations, official
    # rules, backend definitions and licenses; omit only inventory's cache files.
    if snapshot_root is None:add(PLUGIN)
    return path,roots,files,configs,bindings,directories

def execute(bundle,out,trusted_inputs_sha256=None):
    bundle=Path(bundle).resolve();out=Path(out).resolve();record=read_json(bundle/'portable.json')
    if record.get('schema')!=1:raise ValueError('Unknown portable delivery schema')
    from portable_trust import trusted_execution, child_environment
    trusted_execution(bundle,trusted_inputs_sha256)
    if backend_inventory()!=record['backends']:raise ValueError('Portable execution backend differs from recorded dependencies')
    work=bundle/'workspace'
    with tempfile.TemporaryDirectory(prefix='qianxing-portable-run-')as temporary:
        scratch=Path(temporary);trace=scratch/'trace';trace.mkdir()
        beyond_backend = PLUGIN / 'vendor/beyond'
        native_lock = unbundled_canvas_lock(read_json(work / record['job']), beyond_backend)
        env = child_environment()
        if native_lock is not None:
            native_root = scratch / 'native-canvas'
            copy_canvas_payload(bundle / 'native-canvas', native_root, native_lock)
            env['UGC_BEYOND_NATIVE_ROOT'] = str(native_root)
        read_roots=[str(work),str(out.parent),str(scratch),str(Path(sys.base_prefix).resolve()),str(Path(sys.prefix).resolve())]
        package_paths=[]
        for name in('lupa','PIL'):
            spec=importlib.util.find_spec(name)
            if spec and spec.submodule_search_locations:
                read_roots.extend(spec.submodule_search_locations)
                package_paths.extend(str(Path(p).parent)for p in spec.submodule_search_locations)
        boundary={'read_roots':read_roots,'blocked_roots':[str(work/'toolchain')],'write_roots':[str(out.parent),str(scratch)],'trace':str(trace)}
        read_roots.append(str(PLUGIN))
        runner=PLUGIN/'scripts/dependency_runner.py'
        command=[sys.executable,'-X','utf8','-B',str(runner),str(PLUGIN/'scripts/qianxing.py'),'produce',str(work/record['job']),'--out',str(out)]
        env.update(UGC_BUILD_BOUNDARY=json.dumps(boundary), TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch),
                   PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=os.pathsep.join(dict.fromkeys(package_paths)))
        process=subprocess.run(command,cwd=scratch,env=env,capture_output=True,text=True,encoding='utf-8',timeout=900)
        if process.returncode:raise ValueError('Portable build failed: '+(process.stdout+process.stderr)[-18000:])
        traces=list(trace.glob('*.json'));reads=sorted({name for path in traces for name in read_json(path)})
        return {'status':'passed','python_processes':len(traces),'python_read_files':len(reads),'scope':'trusted Python producers and compiler children; external runtime dependencies fingerprinted','editor':'not_checked','host':'not_checked'}

def produce(path,out,evidence,*,job=None,job_digest=None):
    path=Path(path).resolve()
    if job is None:
        source=path.read_bytes()
        job=json.loads(source.decode('utf-8-sig'));job_digest=sha(source)
    original=ProductionInputs({str(path):job_digest})
    path,roots,files,configs,bindings,directories=collect(path,job['portable'],inputs=original)
    backends=backend_inventory()
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
        beyond_backend = PLUGIN / 'vendor/beyond'
        native_lock = unbundled_canvas_lock(job, beyond_backend)
        if native_lock is not None:
            from beyond_native import NATIVE_BINARY, native_library_path
            binary = native_library_path(beyond_backend, lock=native_lock)
            native_root = binary.parents[len(Path(NATIVE_BINARY).parts) - 1]
            copy_canvas_payload(native_root, bundle / 'native-canvas', native_lock)
        write_json(bundle/'portable.json',{'schema':1,'job':files[path],'backends':backends,'original_inputs':original,'relocations':relocations,'files':inventory(bundle),'directories':sorted(p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_dir())})
        snapshot=inventory(bundle)
        with tempfile.TemporaryDirectory(prefix='qianxing-portable-output-',dir=stage.parent)as directory:
            from portable_trust import closure
            result=Path(directory)/'result';execution=execute(bundle,result,closure(bundle)[1])
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
