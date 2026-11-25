"""Unified, isolated Graph Code build pipeline. Python 3.10-3.12; standard library."""
from pathlib import Path
import ast,collections,hashlib,json,os,re,shutil,subprocess,sys,tempfile
from level_inventory import inspect_file,container,fields,vals,unique
from graph_validation import GraphBuildError

PLUGIN=Path(__file__).resolve().parents[1]
RUNTIME=PLUGIN/'vendor/ayaya'
SCHEMA=1

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def resolve_input(value,base):
    p=Path(value).expanduser();return (p if p.is_absolute() else base/p).resolve()
def json_new(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def copy_tree(source,dest):
    if source.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):raise ValueError('Linked resources are not supported')
    shutil.copytree(source,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','out','__workbench_out__'))

def route(kind='game',interface='lua',multiplayer=False,output='gil',task_mode=None,target_domain=None):
    if kind not in ['game','nodes','lua','gil','assets','animation','editor','diagnosis','storage','protocol']:raise ValueError('Unknown task kind')
    if interface not in ['lua','html','native','none']:raise ValueError('Unknown UI implementation')
    if output not in ['gia','gil','both','source']:raise ValueError('Unknown output format')
    from capability_index import DOMAINS,TASK_ENTRYPOINTS,WORKFLOWS
    primary=DOMAINS[{'game':'editor','nodes':'graph','lua':'client','gil':'gil','assets':'assets','animation':'client','editor':'editor','diagnosis':'editor','storage':'editor','protocol':'graph'}[kind]]
    if target_domain is not None and (kind != 'diagnosis' or target_domain not in DOMAINS):
        raise ValueError('Target domain requires a known diagnosis domain')
    diagnosis_domain = target_domain or {'ui':'client','delivery':'gil','assets':'assets'}.get(task_mode)
    if kind == 'diagnosis' and diagnosis_domain:
        primary = DOMAINS[diagnosis_domain]
    helpers=[]
    selected_workflows=[{'animation':'animation','diagnosis':'diagnosis','storage':'storage','protocol':'multiplayer'}[kind]] if kind in ('animation','diagnosis','storage','protocol') else []
    if multiplayer and 'multiplayer' not in selected_workflows:selected_workflows.append('multiplayer')
    for selected in selected_workflows:helpers.extend(DOMAINS[d]for d in WORKFLOWS[selected]['domains'])
    if kind=='game':helpers.append(DOMAINS['graph'])
    if kind in ['game','nodes','gil'] and output in ['gia','gil','both']:helpers.append('miliastra-gil')
    from qianxing_workflow import guide
    workflow=guide(task_mode or {'gil':'delivery','assets':'assets','lua':'ui','diagnosis':'fix'}.get(kind,'feature'))
    routing = {'domain':workflow['domain'],'workflow':workflow,'primary':primary,'support':[x for x in dict.fromkeys(helpers) if x!=primary],
            'decisions':{'kind':kind,'interface':interface,'multiplayer':multiplayer,'output':output},
            'routing_schema':2,'shared_workflows':selected_workflows,'entrypoints':TASK_ENTRYPOINTS[kind],
            'loading':'Primary domain first; support lists available domains, not mandatory reads or execution.',
            'steps':['inspect_current_inputs','define_contracts_and_ownership','query_node_or_API_catalog','author_sources','strict_validate','build_requested_artifacts','readback_and_check_mounts'],
            'missing_contract_policy':'Design and implement new contracts; read and preserve existing contracts. Inspect or create verified bindings; ask only for essential unavailable inputs.',
            'implementation_policy':{'new_contracts':'design_and_implement','existing_contracts':'inspect_and_preserve_or_explicitly_migrate','custom_ids':'allocate_in_verified_namespace_and_check_collisions','platform_ids':'read_from_verified_resources','missing_tool':'inspect_schema_and_implement_adapter','mounts':'implement_supported_binding_then_verify','host_validation':'report_separately_and_continue_offline_work'},
            'contract_resolution_steps':['inspect_current_files_and_definitions','design_new_events_states_signals_and_types','allocate_custom_identifiers_and_check_conflicts','author_graphs_clients_and_required_adapters','write_and_readback_supported_bindings','ask_only_for_unavailable_essential_inputs']}
    if kind == 'diagnosis':
        # Retain the schema-2 string field for legacy readers when the fault object is unknown.
        routing['diagnosis'] = {'entrypoint':'diagnose', 'target_domain':diagnosis_domain,
                                'primary':DOMAINS[diagnosis_domain] if diagnosis_domain else None}
        routing['loading'] = 'Start with shared diagnose. Select a domain from the fault object; the legacy primary field alone is not a loading decision.'
    return routing

def node_definitions(query='',scope='all'):
    normalized=query.casefold().strip()
    items=[];terms=normalized.split()
    for folder in ['client','server'] if scope=='all' else [scope]:
        for p in sorted((RUNTIME/'plugins/nodes'/folder).rglob('*.py')):
            t=ast.parse(p.read_text(encoding='utf-8-sig'))
            for func in [n for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
                for dec in func.decorator_list:
                    if not isinstance(dec,ast.Call) or getattr(dec.func,'id','')!='node_spec':continue
                    meta={}
                    for kw in dec.keywords:
                        try:meta[kw.arg]=ast.literal_eval(kw.value)
                        except (ValueError,TypeError):continue
                    if folder=='server'and meta.get('name')=='创建实体':
                        # Official execution-node contract has no value output.
                        # Preserve vendor source; do not expose its mock return
                        # as a calibrated platform port.
                        meta['outputs']=[p for p in meta.get('outputs',[])if p[1]=='流程']
                    text=json.dumps(meta,ensure_ascii=False).casefold()+' '+func.name.casefold()
                    if terms and not all(term in text for term in terms):continue
                    names=(str(meta.get('name','')).casefold(),func.name.casefold())
                    aliases=meta.get('aliases') or []
                    if isinstance(aliases,str):aliases=[aliases]
                    if normalized in names:
                        rank=0
                    elif normalized and any(s.casefold().startswith(normalized) for s in (*names,*aliases) if isinstance(s,str)):
                        rank=1
                    else:
                        rank=2
                    items.append((rank,{'scope':folder,'call':func.name,'signature':ast.unparse(func.args),
                                       **{k:meta[k] for k in ['name','category','semantic_id','inputs','outputs','description','aliases','dynamic_port_type'] if k in meta},
                                       'implementation':p.relative_to(PLUGIN).as_posix(),
                                       'implementation_line':dec.lineno}))
    items.sort(key=lambda match:match[0])
    return [item for _,item in items]


def catalog(query='',scope='all',limit=20):
    if not isinstance(query,str) or scope not in ('all','client','server') or type(limit)!=int or not 1<=limit<=100:
        raise ValueError('Node query requires a string, all/client/server scope and a limit from 1 to 100')
    items=node_definitions(query,scope)
    nodes=items[:limit]
    for node in nodes:
        source=node['implementation']
        node.update(source={'source_kind':'bundled_graph_code_node_spec','path':source,
                            'line':node['implementation_line'],'sha256':digest(PLUGIN/source)},
                    platform_version=None, platform_applicability='not_checked',
                    editor='not_checked', host='not_checked')
        if (node['scope'],node.get('name'))==('server','创建实体'):
            from platform_profiles import show

            document=show('7.1','mhw66orrrfkm')
            lines=document['content'].splitlines()
            section=lines.index('## **2. 创建实体**')
            end=next(index for index in range(section+1,len(lines)) if lines[index].startswith('## '))
            ports=re.findall(r'^\|\s*(入参|出参)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|',
                             '\n'.join(lines[section:end]),re.M)
            if ports!=[
                ('入参','目标GUID','GUID'),('入参','单位标签索引列表','整数列表'),
            ]:
                raise ValueError('7.1 创建实体 port evidence differs from the calibrated scope')
            node['port_evidence']={
                **{key:document[key] for key in ('id','path','sha256','source_kind','official_url','source_version')},
                'line':section+1, 'scope':'documented_value_ports',
                'documented_inputs':[{'name':name,'type':kind} for _,name,kind in ports],
                'documented_outputs':[],
            }
    result={'matches':len(items),'nodes':nodes}
    if not items:
        result['hint']='Try a shorter node name, a catalog alias, or scope=all.'
    return result

def metadata(path, code=None):
    try:
        tree=ast.parse(path.read_text(encoding='utf-8-sig') if code is None else code,filename=str(path))
    except SyntaxError as exc:
        raise GraphBuildError(str(exc),[{'code':'graph_syntax','severity':'error','message':exc.msg,
                                        'source':str(path),'line':exc.lineno}]) from exc
    text=ast.get_docstring(tree) or ''
    result={k:v.strip() for k,v in re.findall(r'^\s*(graph_id|graph_name|graph_type):\s*(.+)$',text,re.M)}
    if not all(result.get(k) for k in ('graph_id','graph_name','graph_type')):
        message='Graph Code must declare graph_id, graph_name and graph_type'
        raise GraphBuildError(message+': '+str(path),[{'code':'graph_metadata','severity':'error','message':message,'source':str(path)}])
    if result['graph_type'] not in ('server','client'):
        message='Graph Code graph_type must be server or client'
        raise GraphBuildError(message+': '+str(path),[{'code':'graph_scope','severity':'error','message':message,'source':str(path)}])
    if result['graph_type']=='server':
        parents={child:parent for parent in ast.walk(tree)for child in ast.iter_child_nodes(parent)}
        for call in ast.walk(tree):
            if isinstance(call,ast.Call)and isinstance(call.func,ast.Name)and call.func.id=='创建实体'and not isinstance(parents.get(call),ast.Expr):
                message='创建实体 has no value output in the bundled 7.1 node reference; call it as a statement and query the GUID separately'
                raise GraphBuildError(f'{message}: {path}:{call.lineno}',[
                    {'code':'graph_entity_create_output','severity':'error','message':message,'source':str(path),'line':call.lineno},
                ])
    return result

def normalize_new_graph_variables(path,expected):
    """Remove unreferenced calibration variables inherited by the upstream template writer.

    Only applies to new graphs whose declared variable set comes from their generated GIA.
    Existing baseline graphs are checked byte-for-byte separately.
    """
    def vi(n):
        out=bytearray()
        while n>=128:out.append((n&127)|128);n>>=7
        out.append(n);return bytes(out)
    def field(n,payload):return vi((n<<3)|2)+vi(len(payload))+payload
    changed=[];data=path.read_bytes();header,root=container(data);root_out=[]
    for n,w,value,raw in root:
        if n!=10 or w!=2:root_out.append(raw);continue
        section=[]
        for key,wire,payload,record in fields(value):
            if key!=1 or wire!=2:section.append(record);continue
            wrapper=fields(payload);graph_raw=unique(wrapper,1)
            if graph_raw is None:section.append(record);continue
            graph=fields(graph_raw);name=unique(graph,2,default=b'').decode('utf-8',errors='replace')
            if name not in expected:section.append(record);continue
            declared={v['name'] for v in expected[name]['variable_details'] if v['bytes']}
            nodes=vals(graph,3);kept=[];removed=[]
            for gn,gw,gv,gr in graph:
                if gn==6 and gw==2 and gv:
                    variable=unique(fields(gv),2,default=b'').decode('utf-8',errors='replace')
                    if variable not in declared:
                        if not variable or any(variable.encode('utf-8') in node for node in nodes):raise ValueError('Undeclared inherited variable may be referenced: '+variable)
                        removed.append(variable);continue
                kept.append(gr)
            if removed:
                new_graph=b''.join(kept)
                new_wrapper=b''.join(field(a,new_graph) if a==1 and b==2 else r for a,b,v,r in wrapper)
                section.append(field(key,new_wrapper));changed.append({'graph':name,'removed_unreferenced_calibration_variables':removed})
            else:section.append(record)
        root_out.append(field(n,b''.join(section)))
    if changed:
        payload=b''.join(root_out);head=bytearray(data[:20]);head[0:4]=(len(payload)+20).to_bytes(4,'big');head[16:20]=len(payload).to_bytes(4,'big')
        path.write_bytes(bytes(head)+payload+data[-4:])
    return changed

def build(spec_path,out_dir,preserve_container_order=False,structure_bindings=(),*,resolved_bindings=None):
    spec_path=Path(spec_path).resolve();base=spec_path.parent
    from authoring_io import sha
    from native_bindings import Bindings, bindings_for_gil, expand_graph, read_bindings
    spec_bytes=spec_path.read_bytes()
    job=json.loads(spec_bytes.decode('utf-8-sig'))
    if job.get('schema')==2:
        from native_build import build as build_native
        return build_native(spec_path,out_dir)
    if job.get('schema')!=SCHEMA:raise ValueError('Expected build schema 1')
    allowed={'schema','graphs','formats','base_gil','project_resources','include_sections','allowed_top_level_fields','required_mounts','max_stored_nodes','bindings'}
    if set(job)-allowed:raise ValueError('Unknown job keys: '+repr(sorted(set(job)-allowed)))
    graphs=job.get('graphs');formats=job.get('formats',['gia'])
    if not isinstance(graphs,list) or not graphs:raise ValueError('Provide at least one graph source')
    if not isinstance(formats,list) or not formats or set(formats)-{'gia','gil'}:raise ValueError('formats must select gia and/or gil')
    sections=job.get('include_sections',['graphs'])
    if not isinstance(sections,list) or 'graphs' not in sections or set(sections)-{'graphs','signals','structs','templates','instances'}:raise ValueError('Invalid include_sections')
    if set(sections)-{'graphs'} and not job.get('project_resources'):raise ValueError('Additional resources require project_resources')
    allowed_fields=job.get('allowed_top_level_fields',[10])
    if not isinstance(allowed_fields,list) or any(type(n) is not int or n<1 for n in allowed_fields):raise ValueError('Invalid allowed_top_level_fields')
    if 50 in allowed_fields:raise ValueError('Node builds do not replace embedded Lua; use the Lua packaging workflow')
    required_mounts=job.get('required_mounts',[])
    if required_mounts and 'gil' not in formats:raise ValueError('Mount verification requires a GIL output')
    baseline=resolve_input(job['base_gil'],base) if job.get('base_gil') else None
    if 'gil' in formats:
        from level_inventory import calibrated_container
        if not baseline or not baseline.is_file():raise ValueError('GIL output requires an existing base_gil')
        calibrated_container(baseline.read_bytes())
    output=Path(out_dir).resolve()
    if output.exists():raise ValueError('输出目录已存在，请指定新目录，避免覆盖已有产物')
    if output.is_relative_to(PLUGIN):raise ValueError('Build output must be outside the plugin')
    inputs={str(spec_path):sha(spec_bytes)}
    if baseline:inputs[str(baseline)]=digest(baseline)
    bindings=resolved_bindings if resolved_bindings is not None else Bindings()
    if job.get('bindings'):
        path=resolve_input(job['bindings'],base)
        bindings,inputs[str(path)]=read_bindings(path,baseline.read_bytes() if baseline else None)
    sources=[];source_texts={};ids=set();names=set()
    for item in graphs:
        if not isinstance(item,dict) or set(item)-{'source','scope','category'}:raise ValueError('Invalid graph descriptor')
        source=resolve_input(item['source'],base)
        if source.is_symlink() or not source.is_file():raise ValueError('Graph source must be a regular file')
        raw=source.read_bytes();code=raw.decode('utf-8-sig')
        meta=metadata(source,code);scope=item.get('scope',meta['graph_type'])
        if scope not in ['server','client'] or scope!=meta['graph_type']:raise ValueError('Scope does not match Graph Code metadata')
        category=item.get('category','技能节点图' if scope=='client' else '')
        if category not in ['','技能节点图','布尔过滤器节点图','整数过滤器节点图','状态节点图']:raise ValueError('Unsupported graph category')
        if meta['graph_id'] in ids or meta['graph_name'] in names:raise ValueError('Graph IDs and names must be unique')
        ids.add(meta['graph_id']);names.add(meta['graph_name']);sources.append((source,scope,category,meta));inputs[str(source)]=sha(raw)
        source_texts[source]=(raw,expand_graph(code,source,bindings))
    logs=[]
    with tempfile.TemporaryDirectory(prefix='qianxing-node-build-') as td:
        work=Path(td);runtime=work/'runtime';copy_tree(RUNTIME,runtime)
        project=runtime/'assets/资源库/项目存档/BuildProject';project.mkdir(parents=True)
        if job.get('project_resources'):
            resources=resolve_input(job['project_resources'],base)
            from graph_resources import merge_resources
            inputs.update(merge_resources([resources],project))
        stage=work/'delivery';stage.mkdir();(stage/'sources').mkdir();(stage/'models').mkdir();(stage/'gia').mkdir();(stage/'logs').mkdir()
        paths=[]
        for index,(source,scope,category,meta) in enumerate(sources):
            path=project/'节点图'/scope/category/(str(index)+'_'+source.name);path.parent.mkdir(parents=True,exist_ok=True)
            original,compiled=source_texts[source]
            path.write_bytes(compiled.encode('utf-8'));paths.append(path)
            (stage/'sources'/path.name).write_bytes(original)
        source_paths={path:item[0] for path,item in zip(paths,sources)}
        def remap_source_paths(text):
            for staged,original in source_paths.items():
                text=text.replace(str(staged),str(original)).replace(staged.as_posix(),original.as_posix())
                for ascii_only in (False,True):
                    old=json.dumps(str(staged),ensure_ascii=ascii_only)[1:-1]
                    new=json.dumps(str(original),ensure_ascii=ascii_only)[1:-1]
                    text=text.replace(old,new)
            return text

        def call(label,args,*,validation=False):
            cmd=[sys.executable,'-X','utf8','-B',*map(str,args)]
            if os.environ.get('MILIASTRA_WONDERLAND_BUILD_BOUNDARY'):
                cmd=[sys.executable,'-X','utf8','-B',str(PLUGIN/'scripts/dependency_runner.py'),*map(str,args)]
            r=subprocess.run(cmd,cwd=runtime,capture_output=True,text=True,encoding='utf-8',timeout=180)
            diagnostic=remap_source_paths(r.stdout+r.stderr)
            (stage/'logs'/(label+'.txt')).write_text(diagnostic,encoding='utf-8')
            logs.append({'stage':label,'exit_code':r.returncode})
            if r.returncode:
                rows=[]
                if validation and r.stdout.strip():
                    try:rows=json.loads(remap_source_paths(r.stdout))['diagnostics']
                    except (ValueError,KeyError):pass
                if len(diagnostic)>16000:diagnostic=diagnostic[:12000]+'\n[diagnostic truncated]\n'+diagnostic[-4000:]
                raise GraphBuildError(label+' failed:\n'+diagnostic,rows or [
                    {'code':'graph_build_stage_failed','stage':label,'message':diagnostic},
                ])
        runner=runtime/'private_extensions/run_ugc_file_tools.py';up_out=runtime/'private_extensions/ugc_file_tools/out'
        for index,path in enumerate(paths):
            call('validate-'+str(index),[PLUGIN/'scripts/graph_validation.py','--worker',path,runtime],validation=True)
            call('model-'+str(index),[runner,'tool','export_graph_model_json_from_graph_code','--graph-code',path,'--output-json','model_'+str(index)+'.json'])
            shutil.copyfile(up_out/('model_'+str(index)+'.json'),stage/'models'/('model_'+str(index)+'.json'))
        args=[runner,'tool','export_project_graphs_to_gia','--project-root',project,'--out-dir','build_gia']
        for path in paths:args+=['--graph-code',path]
        if baseline:args+=['--base-gil-for-signal-defs',baseline,'--id-ref-gil',baseline]
        if preserve_container_order:args=[PLUGIN/'scripts/gia_backend_adapter.py',*args]
        call('gia-export',args)
        exported=list((up_out/'build_gia').rglob('*.gia'))
        if not exported:raise ValueError('No GIA was generated')
        summaries=[];composite_summaries={};signal_audits=[];gia_structures=[];gia_variable_types=[]
        from native_gia import bind_skill_notifications
        for index,gia in enumerate(exported):
            bound,changes=bind_skill_notifications(gia.read_bytes(),names)
            if changes:gia.write_bytes(bound)
            signal_versions=[]
            if preserve_container_order:
                from native_gia import bind_generated_variable_types
                bound,changes=bind_generated_variable_types(gia.read_bytes())
                if changes:gia.write_bytes(bound);gia_variable_types.extend(changes)
                if structure_bindings:
                    from native_gia import bind_generated_structures
                    bound,changes=bind_generated_structures(gia.read_bytes(),baseline.read_bytes(),structure_bindings)
                    if changes:gia.write_bytes(bound);gia_structures.extend(changes)
                from native_signals import bind_generated_versions
                bound,signal_versions=bind_generated_versions(gia.read_bytes())
                if signal_versions:gia.write_bytes(bound)
            summary=inspect_file(gia);summaries.extend(summary['graphs'])
            if not summary['graphs']:raise ValueError('Generated GIA contains no readable graphs')
            if any(g['dangling_node_refs'] or not g['node_indices_unique'] for g in summary['graphs']+summary['composite_graphs']):raise ValueError('Generated GIA has invalid node references')
            if preserve_container_order:
                from native_core import model,audit
                from native_signals import audit_gia_signals
                signal_issues,signal_unknown,signal_declarations=audit_gia_signals(model(gia.read_bytes()))
                if signal_issues or signal_unknown:raise ValueError('Generated GIA signal audit failed: '+json.dumps({'issues':signal_issues,'unresolved':signal_unknown},ensure_ascii=False))
                if signal_declarations:
                    checked=audit(gia.read_bytes())
                    if checked['status']!='passed':raise ValueError('Generated GIA signal audit failed: '+json.dumps(checked,ensure_ascii=False))
                signal_audits.append({'file':str(index)+'_'+gia.name,'status':'passed','layer':'static','declarations':len(signal_declarations),
                                      'bound_versions':signal_versions})
            if summary['composite_graphs']:
                from native_core import audit
                checked=audit(gia.read_bytes())
                if checked['status']!='passed':raise ValueError('Generated composite GIA audit failed: '+json.dumps(checked,ensure_ascii=False))
            for g in summary['composite_graphs']:
                if g['id']in composite_summaries and g!=composite_summaries[g['id']]:raise ValueError('Conflicting composite graph dependency')
                composite_summaries[g['id']]=g
            shutil.copyfile(gia,stage/'gia'/(str(index)+'_'+gia.name))
        if len(summaries)!=len(sources) or {g['name'] for g in summaries}!=names:raise ValueError('GIA readback graph set differs from requested sources: '+repr({'expected':sorted(names),'actual':[g['name']for g in summaries]}))
        total=sum(g['stored_nodes'] for g in summaries)+sum(g['stored_nodes']for g in composite_summaries.values())
        if 'max_stored_nodes' in job and total>job['max_stored_nodes']:raise ValueError('Configured stored-node budget exceeded')
        gil_result=None
        if 'gil' in formats:
            selection={'selected_graph_code_files':[str(p) for p in paths]}
            selection_path=work/'selection.json'
            # Graph-only builds must not scan other graphs from project_resources.
            selection_arg=[]
            if set(sections)=={'graphs'}:
                selection_path.write_text(json.dumps(selection),encoding='utf-8');selection_arg=['--selection-json',selection_path]
            args=[runner,'project','import','--dangerous','--project-archive',project,'--graphs-strict',*selection_arg]
            for section,flag in [('templates','templates'),('instances','instances'),('structs','structs'),('signals','signals'),('ui','ui-widget-templates')]:
                if section not in sections:args+=['--skip-'+flag]
            newgil=up_out/'level.gil';args += [baseline,newgil];call('gil-writeback',args)
            raw=newgil.read_bytes();calibrated_container(raw)
            bound,changes=bind_skill_notifications(raw,names)
            if changes:newgil.write_bytes(bound)
            normalization=normalize_new_graph_variables(newgil,{g['name']:g for g in summaries})
            if preserve_container_order and structure_bindings:
                from native_core import bind_structures
                newgil.write_bytes(bind_structures(newgil.read_bytes(),structure_bindings))
            if preserve_container_order:
                from level_authoring import pack
                original_order=[n for n,w,v,r in container(baseline.read_bytes())[1]]
                current_header,current_rows=container(newgil.read_bytes());rank={n:i for i,n in reversed(list(enumerate(original_order)))}
                ordered=sorted(enumerate(current_rows),key=lambda item:(rank.get(item[1][0],len(rank)),item[0]))
                newgil.write_bytes(pack(b''.join(row[3]for _,row in ordered),current_header[1:4]))
            before_header,before=container(baseline.read_bytes());after_header,after=container(newgil.read_bytes())
            if before_header[1:4]!=after_header[1:4]:raise ValueError('Container metadata changed unexpectedly')
            if [r for n,_,_,r in before if n not in allowed_fields]!=[r for n,_,_,r in after if n not in allowed_fields]:raise ValueError('Protected field bytes or ordering changed: '+repr(sorted({n for n,_,_,_ in before+after if [r for a,_,_,r in before if a==n]!=[r for a,_,_,r in after if a==n]})))
            by_field=lambda fs:{n:[raw for a,_,_,raw in fs if a==n] for n,_,_,_ in fs}
            a,b=by_field(before),by_field(after)
            changed=sorted(n for n in set(a)|set(b) if a.get(n)!=b.get(n))
            if set(changed)-set(allowed_fields):raise ValueError('Unexpected top-level changes: '+repr(changed))
            inv=inspect_file(newgil)
            original_inventory=inspect_file(baseline)
            if composite_summaries or inv['composite_graphs']or original_inventory['composite_graphs']:
                from native_core import model
                from native_resources import composite_contracts
                actual=composite_contracts(model(newgil.read_bytes()))
                previous=composite_contracts(model(baseline.read_bytes()));expected_names=set()
                for file in exported:
                    for name,expected in composite_contracts(model(file.read_bytes())).items():
                        expected_names.add(name)
                        if actual.get(name)!=expected:raise ValueError('Composite GIL/GIA readback mismatch: '+repr({'name':name,'gil':actual.get(name),'gia':expected}))
                if set(actual)!=set(previous)|expected_names:raise ValueError('GIL composite dependency set differs from source exports')
            for old in original_inventory['composite_graphs']:
                found=[g for g in inv['composite_graphs']if g['id']==old['id']]
                if len(found)!=1 or found[0]['sha256']!=old['sha256']:raise ValueError('Existing composite graph changed unexpectedly')
            preserved_graphs=0
            for old in original_inventory['graphs']:
                if old['name'] in names:raise ValueError('Existing graph replacement requires the dedicated sample-based patch workflow: '+old['name'])
                candidates=[g for g in inv['graphs'] if g['id']==old['id']]
                if len(candidates)!=1 or candidates[0]['sha256']!=old['sha256']:raise ValueError('Existing graph body changed unexpectedly: '+old['name'])
                preserved_graphs+=1
            for name in names:
                found=[g for g in inv['graphs'] if g['name']==name]
                if len(found)!=1:raise ValueError('GIL graph name missing or ambiguous: '+name)
                expect=next(g for g in summaries if g['name']==name)
                compared=['stored_nodes','connections','variables','literal_values' if preserve_container_order else 'pin_values']
                mismatch={key:{'gil':found[0][key],'gia':expect[key]} for key in compared if found[0][key]!=expect[key]}
                if preserve_container_order and 'literal_values' in mismatch:
                    from native_core import model,get,ref,slot
                    from native_model import constant
                    from level_inventory import vals
                    actual_graph=next(g for g in model(newgil.read_bytes())['graphs']if g['name']==name)
                    candidates=[g for file in exported for g in model(file.read_bytes())['graphs']if g['name']==name]
                    if len(candidates)!=1:raise ValueError('Independent GIA graph missing')
                    def literals(graph):
                        output={}
                        for ident,node in graph['nodes'].items():
                            for pin in vals(fields(node),4):
                                kind,index=slot(pin);value=get(pin,3)
                                if kind==3 and value is not None and not vals(fields(pin),5):
                                    result=constant(value);output[(ident,kind,index)]=bool(result)if get(pin,4,0)==4 else result
                        return output
                    actual_literals=literals(actual_graph);expected_literals=literals(candidates[0])
                    added=set(actual_literals)-set(expected_literals);safe=True
                    for key in added:
                        node=actual_graph['nodes'][key[0]];typ=ref(get(node,2,default=b''));pin=next(p for p in vals(fields(node),4)if slot(p)==tuple(key[1:]))
                        if (typ,key[2])==(22,4):
                            # The bundled writer mirrors the explicit trigger Bool at input 3.
                            # An added input is equivalent only when both values match exactly.
                            trigger=expected_literals.get((key[0],3,3))
                            if type(trigger)is not bool or type(actual_literals[key])is not bool or actual_literals[key]!=trigger:safe=False
                        elif (typ,key[2])!=(50,2)or constant(get(pin,3,default=b''))!=0:safe=False
                    if safe and all(k in actual_literals and actual_literals[k]==v for k,v in expected_literals.items()):mismatch.pop('literal_values')
                    elif preserve_container_order:mismatch['literal_values']={'added':[{'port':list(k),'node_type':ref(get(actual_graph['nodes'][k[0]],2,default=b'')),'value':actual_literals[k]}for k in sorted(added)],'changed':[list(k)for k,v in expected_literals.items()if k not in actual_literals or actual_literals[k]!=v]}
                if mismatch:
                    mismatch['variable_details']={'gil':found[0]['variable_details'],'gia':expect['variable_details']}
                    raise ValueError('GIL/GIA semantic readback mismatch: '+json.dumps(mismatch,ensure_ascii=False))
                gil_types={tuple(p[:3]):p[3] for p in found[0]['pin_types'] if p[3] is not None}
                gia_types={tuple(p[:3]):p[3] for p in expect['pin_types'] if p[3] is not None}
                if any(gil_types[k]!=gia_types[k] for k in gil_types.keys()&gia_types.keys()):raise ValueError('Shared explicit port types differ')
                gi={k:v for k,v in gil_types.items()if k[1]==3};ga={k:v for k,v in gia_types.items()if k[1]==3}
                if (any(gi.get(k)!=v for k,v in ga.items())if preserve_container_order else gi!=ga):raise ValueError('Data input port types differ')
                if found[0]['dangling_node_refs']:raise ValueError('GIL contains unresolved node references')
            for mount in required_mounts:
                graph=next((g for g in inv['graphs'] if g['name']==mount['graph_name']),None)
                if graph is None or not any(m['entity_id']==mount['entity_id'] and m['graph_id']==graph['id'] for m in inv['mounts']):raise ValueError('Required entity mount not present: '+repr(mount))
            shutil.copyfile(newgil,stage/'level.gil')
            gil_result={'changed_top_level_fields':changed,'protected_fields_unchanged':True,'inventory':inv,'required_mounts_verified':len(required_mounts),'existing_graph_bodies_preserved':preserved_graphs,'compiler_template_normalization':normalization}
        for path,original in inputs.items():
            if digest(path)!=original:raise ValueError('Input changed while building: '+path)
        if 'gia' not in formats:shutil.rmtree(stage/'gia')
        report={'schema':SCHEMA,'inputs_sha256':inputs,'formats':formats,'graphs':summaries,'composite_graphs':list(composite_summaries.values()),'stored_nodes':total,
                'stages':logs,'gil':gil_result,'mount_contract_checked':bool(required_mounts),'gia_signal_audits':signal_audits,
                'gia_backend_adapters':['registered_signal_events','preserve_client_kernel_2000','bind_omitted_signal_versions','bind_variable_getter_types']if preserve_container_order else[],
                'gia_structure_bindings':gia_structures,
                'gia_variable_type_bindings':gia_variable_types,
                'editor_expanded_nodes':None,'editor_imported':False,'host_tested':False,
                'playable_level_verified':False,'note':'GIA node modules and GIL containers still require editor/runtime acceptance; unconfigured mounts are not fabricated.'}
        if job.get('bindings'):
            report['binding_identity']='passed' if baseline else 'not_checked'
            if gil_result is not None and bindings.ids:
                json_new(stage/'bindings.json',bindings_for_gil((stage/'level.gil').read_bytes(),bindings))
        report['files_sha256']={p.relative_to(stage).as_posix():digest(p) for p in stage.rglob('*') if p.is_file()}
        json_new(stage/'build-report.json',report)
        output.parent.mkdir(parents=True,exist_ok=True)
        # Copy to a sibling staging directory, then publish only the complete build.
        staging=Path(tempfile.mkdtemp(prefix='.node-build-',dir=output.parent))
        try:
            shutil.copytree(stage,staging,dirs_exist_ok=True)
            if output.exists():raise ValueError('Output appeared while building')
            os.rename(staging,output)
        finally:
            if staging.exists():shutil.rmtree(staging)
    return {'output':str(output),'graphs':len(summaries),'stored_nodes':total,'formats':formats,'report':str(output/'build-report.json')}
