"""Schema-2 executable production with final auditing and source-bound evidence."""
from pathlib import Path
import json,re,shutil
from authoring_io import *

def produce(path,out,evidence=None):
    from production_core import _produce as legacy_produce
    job=read_json(path);base=Path(path).parent
    if 'portable'in job:
        from portable_delivery import produce as produce_portable
        return produce_portable(path,out,{}if evidence is None else evidence)
    schema(job,('schema','client','client_check','level','storage','native','assets','protocol','protocol_native','animation','graphs','gil','simulation','experiment','platform','project','ui','resources','beyond'),('schema',))
    if len(job)==1:raise ValueError('No production stages')
    evidence={}if evidence is None else evidence
    inputs={str(path):sha(Path(path).read_bytes())};stages=[];executions=[]
    def track(p):
        p=Path(p).resolve();inputs[str(p)]=sha(p.read_bytes());return p
    def state(name):
        ident=str(len(stages))+':'+name
        executions.append({'id':ident,'name':name,'depends_on':[executions[-1]['id']]if executions else[],'inputs':dict(inputs),'outputs':inventory(stage),'status':'passed'})
        stages.append(name);evidence[name]={'status':'passed','layer':'static'}
    # Resolve external inputs and required executors before generating anything.
    from capabilities import doctor
    environment=doctor()
    if any(k in job for k in('level','native','graphs','gil','storage'))and not environment['node']:raise ValueError('Node is required for native production')
    if 'graphs'in job or 'storage'in job:
        if not environment['python_supported']or not environment['ayaya']:raise ValueError('Bundled backend requires supported Python and Ayaya sources')
    if any(k in job for k in('simulation','experiment'))and not environment['lua53']:raise ValueError('lupa.lua53 is required for declared offline models')
    if job.get('assets')and not environment['pillow']:raise ValueError('Pillow is required for asset generation')
    platform_report=None;platform_configuration=None
    client_contract=None
    ui_spec=None
    resource_check=None
    if 'resources'in job:
        from resource_catalogue import check as check_resources
        from platform_profiles import CATALOGUE
        schema(job['resources'],('spec',),('spec',));resource_check=check_resources(track(resolve(base,job['resources']['spec'])))
        track(CATALOGUE);inputs.update(resource_check['inputs'])
        if resource_check['status']!='passed':raise ValueError('Resource contract incomplete: '+canonical(resource_check['errors']+resource_check['unresolved']))
    if 'ui'in job:
        schema(job['ui'],('spec',),('spec',));ui_spec=read_json(track(resolve(base,job['ui']['spec'])))
    if 'client_check'in job:
        from client_api import API_PATH,PARSER,PARSER_FILES
        schema(job['client_check'],('spec',),('spec',))
        client_contract=read_json(track(resolve(base,job['client_check']['spec'])))
        track(API_PATH);track(PARSER/'SOURCE.json');track(PLUGIN/'scripts/client_ast.cjs')
        for name in PARSER_FILES:track(PARSER/name)
        if not environment['node']:raise ValueError('Node is required for client API checks')
    if resource_check is not None and resource_check['check_client']and client_contract is None:
        raise ValueError('Resource client cross-check requires client_check contract')
    if 'project'in job:
        schema(job['project'],('spec',),('spec',));track(resolve(base,job['project']['spec']))
    if 'platform'in job:
        from platform_profiles import check,CATALOGUE
        schema(job['platform'],('spec',),('spec',))
        config=track(resolve(base,job['platform']['spec']));platform_configuration=read_json(config)
        platform_report=check(platform_configuration);track(CATALOGUE)
        for source in platform_report['sources'].values():track(PLUGIN/source['path'])
        if platform_report['status']!='passed':
            evidence['platform_configuration']={'status':platform_report['status'],'layer':'static','scope':'declared_configuration','report':platform_report}
            raise ValueError('Platform configuration acceptance incomplete: '+canonical(platform_report['checks']))
    if 'client'in job:
        c=job['client']
        if 'assembly'in c:
            from client_assembly import assemble
            cp=track(resolve(base,c['assembly']));_,mapping=assemble(read_json(cp),cp.parent);inputs.update(mapping['inputs'])
        elif 'source'in c:track(resolve(base,c['source']))
    if 'level'in job:
        lp=track(resolve(base,job['level']['spec']));level=read_json(lp)
        for item in level['scripts']:
            if 'source'in item:track(resolve(lp.parent,item['source']))
    if 'native'in job:
        native=job['native'];schema(native,('base','spec','plan'),('base',))
        if ('spec'in native)==('plan'in native):raise ValueError('Choose native spec or plan')
        track(resolve(base,native['base']));np=track(resolve(base,native.get('spec',native.get('plan'))));patch=read_json(np)
        if patch.get('schema')!=2:raise ValueError('Native patch/plan requires schema 2')
        if 'plan'in native:
            for item in patch['inputs'].values():track(resolve(np.parent,item['source']))
        else:
            for op in patch['operations']:
                if 'source'in op:track(resolve(np.parent,op['source']))
    if 'storage'in job:
        from storage_authoring import validate
        sp=track(resolve(base,job['storage']['spec']));validate(read_json(sp))
        if job['storage'].get('base'):track(resolve(base,job['storage']['base']))
    for item in job.get('assets',[]):
        track(resolve(base,item['source']))
        if 'spec'in item:track(resolve(base,item['spec']))
    if 'protocol'in job:
        from production_core import protocol
        protocol(job['protocol'])
        if client_contract is not None:
            if 'protocol'in client_contract and client_contract['protocol']!=job['protocol']:
                raise ValueError('Client protocol contract differs from production protocol')
            client_contract={**client_contract,'protocol':job['protocol']}
    if 'graphs'in job:
        gp=track(resolve(base,job['graphs']['spec']));graph=read_json(gp)
        if graph.get('schema')not in(1,2):raise ValueError('Unknown graph schema')
        for item in graph['graphs']:track(resolve(gp.parent,item['source']))
        if graph.get('base_gil'):track(resolve(gp.parent,graph['base_gil']))
        if graph.get('project_resources'):
            for p in resolve(gp.parent,graph['project_resources']).rglob('*'):
                if p.is_file():track(p)
    for frame in job.get('animation',{}).get('frames',[]):
        if not frame['asset'].startswith('@asset:'):track(resolve(base,frame['asset']))
    for name in('base','source'):
        if name in job.get('gil',{}):track(resolve(base,job['gil'][name]))
    if 'simulation'in job:
        sp=track(resolve(base,job['simulation']['spec']));scene=read_json(sp)
        if scene.get('schema')!=2:raise ValueError('Joint production simulation requires schema 2')
        for item in scene['clients']+([scene['server']]if scene.get('server')else[]):
            if item['source']!='@level':track(resolve(sp.parent,item['source']))
    if 'experiment'in job:
        ep=track(resolve(base,job['experiment']['spec']));experiment=read_json(ep)
        if experiment.get('schema')!=2:raise ValueError('Unknown experiment schema')
        track(resolve(ep.parent,experiment['source']))
    if not environment['lua53']:
        from level_authoring import script_records
        lua_inputs=any(Path(p).suffix.lower()=='.lua'or Path(p).suffix.lower()=='.gil'and script_records(Path(p).read_bytes())for p in inputs)
        if lua_inputs or any(k in job for k in ('client','storage','assets','animation','protocol')):
            raise ValueError('lupa.lua53 is required for final Lua compilation')
    with output_directory(out)as stage:
        if resource_check is not None:
            write_json(stage/'resource-report.json',resource_check)
            resource_rows=[{**row,'source':{k:v for k,v in row['source'].items()if k!='path'}}for row in resource_check['resources']]
            write_json(stage/'resource-catalogue.json',{'schema':2,'version':resource_check['version'],'resources':resource_rows,
                       'complete_platform_catalogue':False})
            state('resource_contract')
            evidence['resource_contract'].update(scope='declared_resource_uses',artifact_references_verified=False,report='resource-report.json')
        write_json(stage/'environment.json',environment)
        if platform_report is not None:
            write_json(stage/'platform-configuration.json',platform_configuration)
            write_json(stage/'platform-report.json',platform_report);state('platform_configuration')
            evidence['platform_configuration'].update(scope='declared_configuration',artifact_verified=False,report='platform-report.json')
        legacy={k:v for k,v in job.items()if k in('protocol','protocol_native','animation')};legacy['schema']=1
        raw=None;storage_spec=None;binding=None;storage_host=None
        if 'client'in job:
            c=job['client']
            if set(c)=={'assembly'}:
                from client_assembly import assemble
                ap=track(resolve(base,c['assembly']));code,mapping=assemble(read_json(ap),ap.parent);inputs.update(mapping['inputs'])
                (stage/'assembled.lua').write_text(code,encoding='utf-8',newline='\n');write_json(stage/'source-map.json',mapping)
                legacy['client']={'source':str(stage/'assembled.lua')};state('client_assembly')
            elif set(c)=={'source'}:legacy['client']={'source':str(track(resolve(base,c['source'])))}
            else:raise ValueError('client selects source or assembly')
        if 'storage'in job:
            from storage_authoring import build,attach
            sp=track(resolve(base,job['storage']['spec']));storage_spec=read_json(sp);build(sp,stage/'storage')
            state('storage_generation')
        if 'assets'in job:
            legacy['assets']=[];asset_names=set()
            for item in job['assets']:
                if not isinstance(item.get('name'),str)or not re.fullmatch(r'[A-Za-z0-9_-]+',item['name'])or item['name']in asset_names:raise ValueError('Unique safe asset names required')
                asset_names.add(item['name'])
                if item.get('kind')=='gia':
                    from native_assets import build
                    source=track(resolve(base,item['source']));sp=track(resolve(base,item['spec']));build(source,sp,stage/'native-assets'/item['name']);state('native_assets')
                else:legacy['assets'].append({**item,'source':str(track(resolve(base,item['source'])))})
            if not legacy['assets']:legacy.pop('assets')
        if 'animation'in legacy:
            for frame in legacy['animation']['frames']:
                if not frame['asset'].startswith('@asset:'):frame['asset']=str(track(resolve(base,frame['asset'])))
        resource_job={k:legacy.pop(k)for k in('assets','protocol','protocol_native','animation')if k in legacy}
        if resource_job:
            resource_job['schema']=1;write_json(stage/'resource-job.json',resource_job)
            resource_report=legacy_produce(stage/'resource-job.json',stage/'resources',{})
            evidence.update(resource_report['evidence']);state('resource_generation')
        if 'level'in job:
            from level_authoring import compile_spec
            lp=track(resolve(base,job['level']['spec']));raw,binding=compile_spec(read_json(lp),lp.parent);inputs.update(binding['source_sha256']);write_json(stage/'client-bindings.json',binding)
            state('level_generation')
        if 'native'in job:
            if raw is not None:raise ValueError('Choose level generation or explicit native baseline')
            from native_core import apply
            p=track(resolve(base,job['native']['base']))
            if 'plan'in job['native']:
                from native_changes import apply_plan
                sp=track(resolve(base,job['native']['plan']));record=read_json(sp)
                raw,r=apply_plan(p.read_bytes(),record,sp.parent);inputs.update(r['inputs'])
                write_json(stage/'native-diff.json',r['difference']);write_json(stage/'native-plan.json',record)
            else:
                sp=track(resolve(base,job['native']['spec']));spec=read_json(sp)
                for op in spec['operations']:
                    if 'source'in op:track(resolve(sp.parent,op['source']))
                raw,r=apply(p.read_bytes(),spec,sp.parent)
            write_json(stage/'native-report.json',r);state('native_apply')
        if ui_spec is not None:
            from native_ui import layout
            if raw is None:raise ValueError('UI stage requires generated level or native baseline')
            bound={**ui_spec,'base_sha256':sha(raw)}if ui_spec.get('base_sha256')=='@level'else ui_spec
            raw,ui_report=layout(raw,bound);write_json(stage/'ui-report.json',ui_report);state('native_ui')
        if storage_spec is not None:
            if raw is None and job['storage'].get('base'):raw=track(resolve(base,job['storage']['base'])).read_bytes()
            if raw is not None:raw=attach(raw,storage_spec)
            storage_host=storage_spec.get('host_entity_id')
            if storage_host is None and 'level'in job:
                from native_core import get
                from level_inventory import fields,vals
                candidates=[]
                for e in vals(fields(get(raw[20:-4],5,default=b'')),1):
                    kinds={get(c,1,0)for c in vals(fields(e),6)}
                    if kinds=={1,3,4,7}:candidates.append(get(e,1,0))
                if len(candidates)!=1:raise ValueError('Generated controller calibration is ambiguous')
                storage_host=candidates[0]
            if raw is not None and storage_host is None:raise ValueError('Existing storage baseline requires host_entity_id')
        if raw is not None:(stage/'base.gil').write_bytes(raw)
        graph_spec=None
        if 'graphs'in job:
            gp=track(resolve(base,job['graphs']['spec']));graph_spec=read_json(gp)
            for item in graph_spec['graphs']:item['source']=str(track(resolve(gp.parent,item['source'])))
            if graph_spec.get('base_gil'):graph_spec['base_gil']=str(track(resolve(gp.parent,graph_spec['base_gil'])))
            elif raw is not None:graph_spec['base_gil']=str(stage/'base.gil')
            if graph_spec.get('project_resources'):
                folder=resolve(gp.parent,graph_spec['project_resources'])
                for f in folder.rglob('*'):
                    if f.is_file():track(f)
                graph_spec['project_resources']=str(folder)
        if storage_spec is not None and raw is not None:
            if graph_spec is None:graph_spec={'schema':2,'graphs':[],'base_gil':str(stage/'base.gil'),'formats':['gia','gil'],'allowed_top_level_fields':[10,6,11,35]}
            resources=stage/'merged-resources'
            if graph_spec.get('project_resources'):shutil.copytree(graph_spec['project_resources'],resources)
            else:resources.mkdir()
            shutil.copytree(stage/'storage/resources',resources,dirs_exist_ok=True)
            graph_spec['project_resources']=str(resources);graph_spec['graphs'].append({'source':str(stage/'storage/storage.py'),'scope':'server'})
            # Native structures/helper declarations were already authored into
            # this baseline. Resources supply Graph Code type information;
            # avoid a second importer rewriting those authoritative declarations.
            graph_spec['include_sections']=list(dict.fromkeys(graph_spec.get('include_sections',['graphs'])+['signals']))
            graph_spec.setdefault('struct_bindings',[]).append({'graph_name':storage_spec['name'],'struct_id':storage_spec['struct_id']})
            graph_spec.setdefault('graph_ids',{})[storage_spec['name']]=storage_spec['graph_id']
        if graph_spec and job.get('protocol_native'):
            resources=stage/'protocol-graph-resources'
            if graph_spec.get('project_resources'):shutil.copytree(graph_spec['project_resources'],resources)
            else:resources.mkdir()
            shutil.copytree(stage/'resources/protocol-native/resources',resources,dirs_exist_ok=True)
            graph_spec['project_resources']=str(resources);graph_spec['include_sections']=list(dict.fromkeys(graph_spec.get('include_sections',['graphs'])+['signals']))
        if graph_spec:
            write_json(stage/'graph-job.json',graph_spec);legacy['graphs']={'spec':str(stage/'graph-job.json')}
        if 'gil'in job:
            g={**job['gil']}
            if 'base'in g:g['base']=str(track(resolve(base,g['base'])))
            elif graph_spec:g['use_graph_output']=True
            elif raw is not None:g['base']=str(stage/'base.gil')
            if 'source'in g:g['source']=str(track(resolve(base,g['source'])))
            if binding and g['mapping']in binding.get('template_aliases',{}):
                from level_authoring import with_template_alias
                source=Path(g['source']if 'source'in g else legacy['client']['source']);original=source.read_bytes()
                patched=with_template_alias(original,binding['template_aliases'][g['mapping']],binding['template_indices'])
                (stage/'bound-client.lua').write_bytes(patched);g['source']=str(stage/'bound-client.lua')
                if(stage/'source-map.json').exists():
                    mapping=read_json(stage/'source-map.json');offset=patched[:len(patched)-len(original)].count(b'\n')
                    for segment in mapping['segments']:segment['start']+=offset;segment['end']+=offset
                    mapping['generated_prefix_lines']=offset;write_json(stage/'source-map.json',mapping)
            legacy['gil']=g
        if raw is not None and 'gil'not in legacy and graph_spec is None:(stage/'level.gil').write_bytes(raw)
        if len(legacy)>1:
            write_json(stage/'legacy-job.json',legacy);r=legacy_produce(stage/'legacy-job.json',stage/'build',{})
            for p,digest in r['source_sha256'].items():
                if not Path(p).is_relative_to(stage):inputs[p]=digest
            for k,v in r['evidence'].items():evidence[k]=v
            final=stage/'build/level.gil'
            if not final.exists():final=stage/'build/graphs/level.gil'
            if final.exists():shutil.copyfile(final,stage/'level.gil')
            state('production')
        if (stage/'level.gil').exists():
            if 'client'in job and 'gil'not in job:raise ValueError('Embedding a client stage requires an explicit gil.mapping')
            if job.get('protocol_native')and job.get('protocol',{}).get('schema')==2:
                from client_signal_binding import bind_replies
                outgoing=[s for s in job['protocol']['signals']if s['direction']=='server_to_client']
                if outgoing:
                    raw,bound=bind_replies((stage/'level.gil').read_bytes(),[s['name']for s in outgoing],{s['name']:s.get('target','signal_source')for s in outgoing})
                    (stage/'level.gil').write_bytes(raw);write_json(stage/'protocol-client-targets.json',bound)
            if job.get('protocol_native'):
                from protocol_codegen import check_gil
                evidence['protocol_native']=check_gil(stage/'level.gil',read_json(stage/'resources/protocol-native/wire.json'))
            if storage_spec is not None:
                from client_signal_binding import bind_replies
                s=storage_spec
                prefix=s['name']+('_v3_'if s['schema']==3 else'_')
                replies=[prefix+kind+'_'+str(i)+'_reply'for i in range(1,s['slots']+1)for kind in(('read','open','write')if s['schema']==3 else('read','write'))]
                replies += [s['name']+'_achievement_'+str(a['id'])+'_reply'for a in s.get('achievements',[])]
                raw,bound=bind_replies((stage/'level.gil').read_bytes(),replies);(stage/'level.gil').write_bytes(raw);write_json(stage/'client-replies.json',bound)
                from native_core import apply,model
                graphs=[g for g in model(raw)['graphs']if g['name']==s['name']]
                if len(graphs)!=1:raise ValueError('Generated storage graph missing')
                patch={'schema':2,'base_sha256':sha(raw),'allowed_top_level_fields':[5,6],'operations':[{'op':'mount','entity_id':storage_host,'graph_id':graphs[0]['id']}]}
                raw,mounted=apply(raw,patch,stage);(stage/'level.gil').write_bytes(raw);write_json(stage/'storage-mount.json',mounted)
                evidence['mounts']={'status':'passed','report':'storage-mount.json','verified_generated_graphs':1}
            from native_core import audit
            result=audit((stage/'level.gil').read_bytes());write_json(stage/'native-audit.json',result)
            if result['status']!='passed':raise ValueError('Final native audit failed: '+canonical(result))
            state('native_audit')
            if ui_spec is not None:
                from native_ui import layout
                final_ui=(stage/'level.gil').read_bytes()
                compared,ui_report=layout(final_ui,{**ui_spec,'base_sha256':sha(final_ui)})
                if compared!=final_ui:raise ValueError('Final native UI differs from declared layout')
                write_json(stage/'ui-report.json',ui_report)
                evidence['native_ui'].update(report='ui-report.json',scope=ui_report['scope'],parent_geometry_verified=False)
            from level_authoring import inspect_bindings
            write_json(stage/'client-bindings.json',inspect_bindings((stage/'level.gil').read_bytes()))
            if 'gil'in legacy:
                from joint_simulator import script_from_gil
                g=legacy['gil'];code,_=script_from_gil((stage/'level.gil').read_bytes(),g['mapping'])
                expected=Path(g.get('source',legacy.get('client',{}).get('source',''))).read_bytes().decode('utf-8-sig')
                if code!=expected:raise ValueError('Final embedded Lua differs from selected client source')
                (stage/'client.lua').write_text(code,encoding='utf-8',newline='\n')
                if(stage/'source-map.json').exists():
                    source_map=read_json(stage/'source-map.json');source_map.update(embedded_source_sha256=sha(code.encode('utf-8')),embedded_mapping=g['mapping']);write_json(stage/'source-map.json',source_map)
        if platform_configuration is not None and 'native_bindings'in platform_configuration:
            from platform_native import check as check_platform_native
            if not(stage/'level.gil').exists():raise ValueError('Platform native bindings require final GIL')
            native_platform=check_platform_native((stage/'level.gil').read_bytes(),platform_configuration)
            write_json(stage/'platform-native-report.json',native_platform)
            if native_platform['status']!='passed':raise ValueError('Final platform native binding incomplete: '+canonical(native_platform['checks']))
            state('platform_native');evidence['platform_native'].update(layer='readback',scope=native_platform['scope'],report='platform-native-report.json',whole_artifact_verified=False)
        if 'project'in job or (stage/'level.gil').exists():
            from project_index import build as index_native,inspect as inspect_project
            final=(stage/'level.gil').read_bytes()if (stage/'level.gil').exists()else None
            if 'project'in job and final is not None:
                project_spec=read_json(resolve(base,job['project']['spec']))
                if sum(a.get('source')=='@level'for a in project_spec.get('artifacts',[]))!=1:
                    raise ValueError('Project checks require exactly one @level final artifact')
            project_report=inspect_project(resolve(base,job['project']['spec']),final)if 'project'in job else index_native(final)
            inputs.update(project_report.get('inputs',{}))
            write_json(stage/'project-report.json',project_report)
            if project_report['status']!='passed':raise ValueError('Final project reference check failed: '+canonical(project_report['issues']+project_report['unresolved']))
            state('project_references');evidence['project_references'].update(scope=project_report['scope'],complete_reference_index=False,report='project-report.json')
        # Inspect the final container after every native mutation and Lua writeback,
        # including mappings that were never materialized as loose .lua files.
        from client_check import inspect as inspect_client
        client_reports=[]
        api_target=stage/'level.gil'if (stage/'level.gil').exists()else stage/'build/client.lua'
        if client_contract is not None:
            if not api_target.exists():raise ValueError('API contract requires final GIL or client Lua')
            write_json(stage/'client-api-contract.json',client_contract)
        if (stage/'level.gil').exists():
            source_map=read_json(stage/'source-map.json')if (stage/'source-map.json').exists()else None
            client_reports.append({'artifact':'level.gil',**inspect_client(stage/'level.gil',source_map=source_map,contract=client_contract)})
        for source in sorted(stage.rglob('*.lua')):
            if 'graphs'in source.relative_to(stage).parts:continue
            client_reports.append({'artifact':source.relative_to(stage).as_posix(),**inspect_client(source,contract=client_contract if source==api_target else None)})
        client_status='failed'if any(r['status']=='failed'for r in client_reports)else'not_checked'if any(r['status']=='not_checked'for r in client_reports)else'passed'if any(r['scripts']for r in client_reports)else'not_applicable'
        api_status=next((r['checks']['api']for r in client_reports if 'contract_sha256'in r),'not_checked')
        client_report={'schema':2,'status':client_status,'layer':'static','artifacts':client_reports,
                       'api':api_status,'references':'not_checked','editor':'not_checked','host':'not_checked'}
        write_json(stage/'client-check.json',client_report)
        state('client_check');evidence['client_check'].update(status=client_status,report='client-check.json',scope='final_embedded_and_loose_Lua')
        executions[-1]['status']=client_status
        syntax_status='failed'if any(r['checks']['syntax']=='failed'for r in client_reports)else'passed'if any(r['scripts']for r in client_reports)else'not_applicable'
        evidence['client_syntax']={'status':syntax_status,'layer':'static','report':'client-check.json','scope':'final_embedded_and_loose_Lua'}
        evidence['client_api']={'status':api_status,'layer':'static','report':'client-check.json','scope':'contract_bound_final_client'}
        if client_status in ('failed','not_checked'):raise ValueError('Final Lua check failed: '+canonical(client_report))
        if resource_check is not None and resource_check['check_client']:
            from resource_catalogue import check_client as check_client_resources
            target_name=api_target.relative_to(stage).as_posix()
            target_report=next(r for r in client_reports if r['artifact']==target_name)
            references=check_client_resources(target_report,resource_check)
            write_json(stage/'client-resource-report.json',references)
            if references['status']!='passed':raise ValueError('Final client resource check incomplete: '+canonical(references))
            state('client_resource_references');evidence['client_resource_references'].update(scope=references['scope'],report='client-resource-report.json',complete_reference_index=False)
        if 'simulation'in job:
            from joint_simulator import run
            sp=track(resolve(base,job['simulation']['spec']));scene=read_json(sp)
            for item in scene['clients']:
                item['source']=str(stage/'level.gil')if item['source']=='@level'else str(track(resolve(sp.parent,item['source'])))
            if scene.get('server'):scene['server']['source']=str(stage/'level.gil')if scene['server']['source']=='@level'else str(track(resolve(sp.parent,scene['server']['source'])))
            result=run(scene,sp.parent,job['simulation'].get('timeout',30));write_json(stage/'simulation.json',result)
            if result['acceptance']['status']!='passed':
                evidence['simulation']={'status':'failed','coverage':result['acceptance']}
                raise ValueError('Required simulation acceptance incomplete: '+str(result['acceptance']['gaps']))
            state('simulation');evidence['simulation']['layer']='lua_model'
            evidence['lua_model']={'status':'passed','report':'simulation.json'}
            evidence['native_graph_model']={'status':result['evidence']['native_graph_model'],'report':'simulation.json'if scene.get('server')else None}
        if 'experiment'in job:
            from experiments import execute
            ep=track(resolve(base,job['experiment']['spec']));r=execute(read_json(ep),ep.parent);inputs.update(r['inputs']);write_json(stage/'experiment.json',r)
            if not r['passed']:
                evidence['experiment']={'status':'failed','observations':r};raise ValueError('Experiment contains failures; see production evidence')
            state('experiment');evidence['experiment']['layer']='simulation'
        if 'beyond'in job:
            from beyond_backend import run as run_beyond
            schema(job['beyond'],('spec','backend'),('spec',))
            external=track(resolve(base,job['beyond']['spec']))
            outcome=run_beyond(external,resolve(base,job['beyond']['backend']) if 'backend'in job['beyond'] else None,stage/'beyond',final_gil=stage/'level.gil')
            inputs.update({p:h for p,h in outcome['inputs'].items() if not Path(p).is_relative_to(stage)})
            state('external_simulation');evidence['external_simulation'].update(layer='external_lua_model',report='beyond/external-simulation.json')
            preview=read_json(stage/'beyond/external-simulation.json')
            evidence['external_software_preview']={'status':preview['rendering'],'layer':'software_preview','report':'beyond/render.json' if preview['preview_generated'] else None}
        # Record executable sources and the bundled backend actually used.
        for p in (PLUGIN/'scripts').glob('*'):
            if p.is_file():track(p)
        if graph_spec:
            for p in (PLUGIN/'vendor/ayaya').rglob('*'):
                if p.is_file()and '__pycache__'not in p.parts and p.suffix not in('.pyc','.pyo'):track(p)
        state('source_integrity')
        write_json(stage/'dependency-graph.json',{'schema':2,'executions':executions,'external_and_tool_inputs':inputs,'final_artifacts':inventory(stage)})
        for name in('lua_model','native_graph_model','compilation_readback','software_preview'):
            evidence.setdefault(name,{'status':'not_applicable'})
        if graph_spec:evidence['compilation_readback']={'status':'passed','report':'build/graphs/replacement-report.json'if graph_spec.get('schema')==2 else'build/graphs/build-report.json'}
        if any(item.get('kind')=='gia'for item in job.get('assets',[])):evidence['software_preview']={'status':'passed','path':'native-assets'}
        evidence['editor']={'status':'not_checked'};evidence['host']={'status':'not_checked'};evidence['real_storage_reentry']={'status':'not_checked'}
        evidence['v3_pipeline']={'status':'passed'}
        # Copy only stable reviewable artifacts; internal jobs contain temporary paths.
        for file in ('legacy-job.json','graph-job.json','resource-job.json'):
            if(stage/file).exists():(stage/file).unlink()
        report=finish(stage,inputs,kind='production',specification=str(Path(path).resolve()),stages=stages,evidence=evidence)
        write_json(stage/'production-report.json',report)
        from delivery_artifacts import roles
        report['files']={name:digest for name,digest in inventory(stage).items()if name!='manifest.json'}
        report['artifacts']=roles(report['files'])
        write_json(stage/'manifest.json',report)
    return report
