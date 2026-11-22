"""Read-only engineering identities and calibrated dependency/consumer queries."""
from pathlib import Path
from collections import Counter,defaultdict,deque
from urllib.parse import quote
import argparse,json
from authoring_io import DiagnosticError,sha,read_json,schema,resolve
from level_inventory import container,fields,vals,unique,graph_records,entity_graph_ids,graph_library_ids
from level_authoring import inspect_bindings,ui_records,stream
from native_core import model,audit,get,ref,slot,definition_id,node_catalog


def key(*parts):return '/'.join(quote(str(p),safe='')for p in parts)


def build(data,namespace='level',*,include_scene=True,include_gameplay=True,validation=None):
    m=model(data);validation=audit(data) if validation is None else validation;header,root=container(data)
    objects=[];references=[];variable_accesses=[];issues=list(validation['issues']);unknown=list(validation['unresolved'])
    def obj(kind,ident,name='',scope=(),**details):
        ident_key=key(namespace,kind,*scope,ident)
        objects.append({'key':ident_key,'artifact':namespace,'kind':kind,'id':ident,'name':name,'scope':list(scope),**details})
        if ident is None or ident=='':issues.append({'error':'object identity absent','key':ident_key})
        return ident_key
    def link(source,target,relation,**location):
        references.append({'source':source,'target':target,'relation':relation,'location':location})
    document=obj('document','root',m['format'],sha256=sha(data))
    definitions=m['definitions'];builtin,_=node_catalog();builtin_used=set()
    from native_signals import declarations,legacy_client_senders
    from native_ports import client_contract,declared_kernel_matches,resolve_dynamic
    signal_records=declarations(m)
    legacy_senders=legacy_client_senders(m,signal_records) if m['format']=='gil' else set()
    roles={i:(r['name'],r['role'])for i,r in signal_records.items()} if m['format']=='gia' else {}
    for s in m['signals']:
        for role in(1,2,7,9):
            locator=get(s,role)
            if locator:roles[ref(locator)]=(get(s,3,default=b'').decode('utf-8'),role)
    resolved_graphs={};connections={}
    # Concrete builtin variants have their own IDs; they remain external definitions.
    builtin_ids=set(builtin)|{v['ConcreteId']for item in builtin.values()for v in item.get('TypeMappings',[])}
    def client_builtin(source,node,descriptor,relation):
        # Client kernel IDs are reused by unrelated shells, and zero can be
        # represented by an omitted locator field. Use the complete identity.
        shell=get(node,2,default=b'')
        ident=get(descriptor,5,0,0)
        scope=('client',get(shell,2,0),ref(shell),get(descriptor,2,0))
        target=key(namespace,'builtin_node',*scope,ident)
        if target not in builtin_used:
            obj('builtin_node',ident,builtin.get(ref(shell),{}).get('Name',''),scope,
                external=True,definition_source='native_client_port_contract')
            builtin_used.add(target)
        link(source,target,relation)
    def node_type(source,ident,relation):
        if ident in definitions:target=key(namespace,'definition',ident)
        elif ident in builtin_ids:
            target=key(namespace,'builtin_node',ident)
            if ident not in builtin_used:
                obj('builtin_node',ident,builtin.get(ident,{}).get('Name',''),external=True,definition_source='bundled_node_catalogue');builtin_used.add(ident)
        else:target=key(namespace,'definition',ident)
        link(source,target,relation)
    for ident,d in definitions.items():
        owner=obj('definition',ident,get(d,200,default=b'').decode('utf-8'),version=get(get(d,4,default=b''),5,0,0))
        target=get(get(d,4,default=b''),4)
        if target:link(owner,key(namespace,'graph','composite',ref(target)),'composite_body')
    for g in m['graphs']+m['composite_graphs']:
        scope=(g['kind'],g['id']);owner=obj('graph',g['id'],g['name'],(g['kind'],))
        resolved_graphs[scope]={}
        for ident,n in g['nodes'].items():
            resolved,_=resolve_dynamic(n,definitions,m['signals'],roles);resolved_graphs[scope][ident]=resolved
            source=obj('node',ident,'',scope,definition_id=definition_id(resolved,definitions),stored_ports=[list(slot(p))for p in vals(fields(n),4)])
            link(owner,source,'contains_node')
            if resolved!=n:node_type(source,definition_id(resolved,definitions),'resolved_node_type')
            for field,relation in((2,'generic_node_type'),(3,'concrete_node_type')):
                descriptor=get(n,field)
                if descriptor:
                    if client_contract(n) is not None:client_builtin(source,n,descriptor,relation)
                    elif (field==3 and ref(get(n,2,default=b'')) in legacy_senders and
                          declared_kernel_matches(n,definitions[ref(get(n,2,default=b''))])):
                        client_builtin(source,n,descriptor,relation)
                    else:node_type(source,ref(descriptor),relation)
            for p in vals(fields(n),4):
                for c in vals(fields(p),5):
                    remote=get(c,2,default=b'');own_port=slot(p)
                    remote_port=(get(remote,1,0,0),get(remote,2,0,0))
                    target=key(namespace,'node',*scope,get(c,1,0))
                    # References consistently point from the consumer to its
                    # provider, irrespective of which endpoint stores the edge.
                    consumer,provider,input_port,output_port=(target,source,remote_port,own_port)if own_port[0]in(2,4)else(source,target,own_port,remote_port)
                    identity=(consumer,provider,input_port,output_port)
                    recorded={'node':ident,'port':list(own_port)}
                    if identity not in connections:
                        location={'input_port':list(input_port),'output_port':list(output_port),'serialized_at':[]}
                        connections[identity]=location
                        references.append({'source':consumer,'target':provider,'relation':'node_connection','location':location})
                    location=connections[identity]
                    if recorded in location['serialized_at']:
                        issues.append({'error':'duplicate node connection record','source':consumer,'target':provider,**recorded})
                    location['serialized_at'].append(recorded)
        from native_graph_variables import read as graph_variables,summary as graph_variable_summary,accesses as graph_variable_accesses
        for record in graph_variables({'graphs':[g],'composite_graphs':[]}):
            name=record['name']
            variable=obj('graph_variable',name,name,scope,**{k:v for k,v in graph_variable_summary(record).items()if k!='name'})
            link(owner,variable,'declares_variable')
        for access in graph_variable_accesses({**m,'graphs':[g],'composite_graphs':[]}):
            source=key(namespace,'node',*scope,access['node'])
            variable_accesses.append({**access,'artifact':namespace,'source':source})
            if access['resolution']=='declared':
                link(source,key(namespace,'graph_variable',*scope,access['name']),
                     'graph_variable_'+access['operation'],value_port=access['value_port'])
        if g['kind']=='composite':
            for mapping in vals(fields(g['raw']),4):
                link(owner,key(namespace,'node',*scope,get(mapping,2,0)),'composite_interface',port=list(slot(mapping)))
    from native_scene import ordinary_object,spatial_objects

    placed = {}
    spatial = spatial_objects(header, root) if include_scene else {}
    if include_scene and m['format'] == 'gil':
        for section in vals(root, 5):
            for raw in vals(fields(section), 1):
                try:
                    scene = ordinary_object(raw)
                except ValueError:
                    # The general index also reads records outside this calibrated scene subset.
                    continue
                if scene is not None:
                    placed[scene['record_id']] = scene
    for entity in m['entities']:
        kind = 'template' if entity['section'] == 4 else 'entity'
        scene = placed.get(entity['entity_id']) if kind == 'entity' else None
        details = spatial.get((kind, entity['entity_id']))
        obj(kind, entity['entity_id'], name=(details or scene or {}).get('name',''),
            **({'scene': scene} if scene else {}), **({'spatial': details} if details else {}))
    from native_variables import summary,audit as audit_variables
    variables=defaultdict(dict)
    for record in m['custom_variables']['records']:
        kind='template'if record['section']==4 else'entity';ident=record['entity_id'];name=record['name']
        variable=obj('custom_variable',name,name,(kind,ident),**{k:v for k,v in summary(record).items()if k!='name'})
        variables[(kind,ident)][name]=variable
        link(key(namespace,kind,ident),variable,'declares_custom_variable')
    for mount in m['mounts']:
        source=key(namespace,'template'if mount['section']==4 else'entity',mount['entity_id'])
        link(source,key(namespace,'graph','ordinary',mount['graph_id']),'graph_mount')
    for gid in m['graph_library']:link(document,key(namespace,'graph','ordinary',gid),'graph_library')
    external_templates=set()
    for section in vals(root,5)if m['format']=='gil'else[]:
        for entity in vals(fields(section),1):
            source=key(namespace,'entity',get(entity,1,0))
            for descriptor in vals(fields(entity),2):
                target=get(descriptor,1,0);category=get(descriptor,2,0,0)
                if category==0:
                    link(source,key(namespace,'template',target),'entity_template')
                    own=variables[('entity',get(entity,1,0))]
                    for name,variable in variables[('template',target)].items():
                        link(own.get(name,source),variable,'overrides_custom_variable'if name in own else'inherits_custom_variable')
                elif category==1:
                    # Platform locator form observed in the preserved level entity.
                    # Identity is recorded, not certified against a platform asset catalogue.
                    if target not in external_templates:
                        obj('platform_template',target,external=True,resource_verified=False);external_templates.add(target)
                    link(source,key(namespace,'platform_template',target),'platform_template')
                else:unknown.append({'entity':get(entity,1,0),'error':'uncalibrated template locator category','category':category})
    for s in m['structs']:
        ident=get(get(s,1,default=b''),1,0);obj('structure',ident)
    for t in m['storage_templates']:
        ident=get(t,1,0);source=obj('storage_template',ident)
        for raw in vals(fields(get(t,2,default=b'')),2):
            target=obj('storage_slot',get(raw,1,0),'',(ident,));link(source,target,'storage_slot')
    from native_structures import audit_references
    traced=[];resolved_model={**m,**{group:[{**g,'nodes':resolved_graphs[(g['kind'],g['id'])]}for g in m[group]]for group in('graphs','composite_graphs')}}
    audit_references(resolved_model,traced)
    audit_variables(m,traced)
    from native_graph_variables import audit as audit_graph_variables
    audit_graph_variables(m,traced)
    for item in traced:
        c=item['context']
        if 'graph_variable'in c:source=key(namespace,'graph_variable',c['graph_kind'],c['graph'],c['graph_variable'])
        elif 'custom_variable'in c:source=key(namespace,'custom_variable','template'if c['section']==4 else'entity',c['entity_id'],c['custom_variable'])
        elif 'definition'in c:source=key(namespace,'definition',c['definition'])
        elif 'storage_template'in c:source=key(namespace,'storage_slot',c['storage_template'],c['storage_slot'])
        elif 'graph'in c:source=key(namespace,'node',c['graph_kind'],c['graph'],c['node'])
        else:source=key(namespace,'structure',c['struct_id'])
        link(source,key(namespace,'structure',item['struct_id']),item['relation'],**c)
    for s in m['signals']:
        name=get(s,3,default=b'').decode('utf-8');source=obj('signal',name,name)
        for role in(1,2,7,9):
            raw=get(s,role)
            if raw:
                target=key(namespace,'definition',ref(raw));link(source,target,'signal_role',role=role);link(target,source,'signal_contract',role=role)
    for ident in sorted(legacy_senders):
        signal=signal_records[ident];source=key(namespace,'definition',ident)
        link(source,key(namespace,'signal',signal['name']),'signal_contract',role=7)
        for field,peer in signal['peers'].items():
            link(source,key(namespace,'definition',ref(peer)),'signal_peer',field=field)
    if m['format']=='gia':
        names=set()
        for ident,s in signal_records.items():
            if s['name']not in names:obj('signal',s['name'],s['name']);names.add(s['name'])
            source=key(namespace,'definition',ident);link(source,key(namespace,'signal',s['name']),'signal_contract',role=s['role'])
            for role,peer in s['peers'].items():
                if peer:link(source,key(namespace,'definition',ref(peer)),'signal_peer',role=role)
        for resource in m['resources']:
            detail=spatial.get(('gia_resource',resource['id'])) if resource['class']==1 else None
            source=obj('gia_resource',resource['id'],detail['name'] if detail else '',(resource['class'],),
                       **({'spatial':detail} if detail else {}))
            for category,ident in resource['references']:link(source,key(namespace,'gia_resource',category,ident),'gia_dependency')
        for unit in vals(root,1)+vals(root,2):
            locator=get(unit,1,default=b'');source=key(namespace,'gia_resource',get(locator,2,0,0),get(locator,4,0,0))
            for field,kind in((13,'graph'),(14,'definition'),(22,'structure')):
                wrapper=get(unit,field)
                if wrapper is None:continue
                body=get(wrapper,1,default=b'')
                if field==13:
                    graph=get(body,1,default=b'');loc=get(graph,1,default=b'')
                    target=key(namespace,kind,'composite'if get(loc,3,0)==21002 else'ordinary',ref(loc))
                elif field==14:target=key(namespace,kind,ref(get(get(get(body,1,default=b''),4,default=b''),1,default=b'')))
                else:target=key(namespace,kind,get(get(body,1,default=b''),1,0))
                link(source,target,'gia_resource_body')
    if m['format']=='gil':
        bindings=inspect_bindings(data)
        issues.extend({'error':message,'domain':'client_bindings'}for message in bindings['diagnostics'])
        for s in bindings['scripts']:obj('script',s['id'],s['name'],sha256=s['sha256'],bytes=s['bytes'])
        records=ui_records(data);parents={};children=[];child_lists=set()
        for fs in records:
            ident=unique(fs,501,0);name=''
            for c in vals(fs,505):
                if get(c,501,0)==2:name=get(get(c,12,default=b''),501,default=b'').decode('utf-8')
            source=obj('control',ident,name)
            parent=unique(fs,504,0)
            if parent is not None:
                parents[ident]=parent;link(source,key(namespace,'control',parent),'ui_parent')
            if vals(fs,503):child_lists.add(ident)
            for packed in vals(fs,503):
                for child in stream(packed):children.append((ident,child));link(source,key(namespace,'control',child),'ui_child')
            for raw in vals(fs,502):
                kind=(get(raw,501,0),get(raw,502,0))
                if kind==(1,5)and get(get(raw,11,default=b''),501,0)!=ident:
                    issues.append({'error':'UI self identity mismatch','control':ident})
                elif kind==(3,3):link(source,key(namespace,'control',get(get(raw,13,default=b''),501,0)),'ui_template')
                elif kind==(4,4):
                    for packed in vals(fields(get(raw,14,default=b'')),501):
                        for target in stream(packed):link(source,key(namespace,'control',target),'ui_template_entry')
            for c in vals(fs,505):
                if (get(c,501,0),get(c,502,0))!=(62,82):continue
                targets=[]
                for override in vals(fields(c),503):
                    if get(override,501,0)==64:
                        target=get(get(override,73,default=b''),501,0)
                        targets.append(target)
                        link(source,key(namespace,'control',target),'ui_root_control')
                if len(targets)!=1:issues.append({'error':'UI root binding missing or duplicated','control':ident})
        for binding in bindings['script_bindings']:
            link(key(namespace,'control',binding['control_guid']),key(namespace,'script',binding['script_guid']),'script_mount')
        for section in vals(root,9):
            for packed in vals(fields(section),501):
                for ident in stream(packed):link(document,key(namespace,'control',ident),'ui_registry')
        # A stored child list is authoritative where present; template links are
        # not parent edges, and shared client-root controls are legal.
        listed=Counter(children)
        for (parent,child),count in listed.items():
            if count>1:issues.append({'error':'duplicate UI child','parent':parent,'child':child})
            if parents.get(child)!=parent:issues.append({'error':'UI child/parent mismatch','parent':parent,'child':child})
        for ident in parents:
            if parents[ident]in child_lists and (parents[ident],ident)not in listed:
                issues.append({'error':'UI parent/child mismatch','parent':parents[ident],'child':ident})
            visited=set();current=ident
            while current in parents:
                if current in visited:
                    issues.append({'error':'UI parent cycle','control':ident});break
                visited.add(current);current=parents[current]
        forward=Counter((r['source'],r['target'])for r in references if r['relation']=='ui_template')
        for r in references:
            if r['relation']=='ui_template_entry'and forward[(r['target'],r['source'])]!=1:
                issues.append({'error':'UI reverse template mismatch',**r})
    unique_relations={'script_mount','graph_mount','ui_template','ui_template_entry','ui_root_control','ui_registry'}
    for triple,count in Counter((r['source'],r['target'],r['relation'])for r in references if r['relation']in unique_relations).items():
        if count>1:issues.append({'error':'duplicate reference','source':triple[0],'target':triple[1],'relation':triple[2]})
    counts=Counter(o['key']for o in objects)
    for ident,count in counts.items():
        if count>1:issues.append({'error':'duplicate object identity','key':ident,'count':count})
    for r in references:
        count=counts[r['target']];r['resolution']='resolved'if count==1 else'ambiguous'if count else'missing'
        if count!=1:issues.append({'error':'ambiguous reference'if count else'dangling reference',**r})
    if include_gameplay and m['format']=='gil':
        from native_gameplay_index import build_gameplay
        gameplay=build_gameplay(data,namespace)
        objects.extend(o for o in gameplay['objects'] if o['key'] not in counts)
        references.extend(gameplay['references'])
        issues.extend(gameplay['issues'])
    script_mappings = [
        {'mapping':o['name'],'id':o['id'],'key':o['key'],'artifact':o['artifact'],'sha256':o['sha256']}
        for o in objects if o['kind']=='script'
    ]
    return {'schema':2,'status':'failed'if issues else'not_checked'if unknown else'passed','artifacts':{namespace:{'format':m['format'],'sha256':sha(data)}},
            'objects':objects,'script_mappings':script_mappings,'references':references,'graph_variable_accesses':variable_accesses,'issues':issues,'unresolved':unknown,'scope':'calibrated native and client object references',
            'complete_reference_index':False,'unindexed':['arbitrary_component_payloads','custom_variable_access_and_literal_targets','graph_variable_dynamic_access_and_overrides','implicit_graph_structure_identity','untyped_numeric_constants','dynamic_Lua_identifiers','platform_resource_catalogue'],
            'editor':'not_checked','host':'not_checked'}


def build_scene(data, namespace='level'):
    """Index the scene and serialized mounts without interpreting graph ports."""
    from native_scene import GIL_HEADER, STATIC_GIA_HEADER, identified_records, spatial_objects, typed_record

    header, root = container(data)
    if header[1:4] not in (GIL_HEADER, STATIC_GIA_HEADER):
        raise ValueError('Scene scope requires calibrated GIL or GIA framing')
    fmt = 'gil' if header[1:4] == GIL_HEADER else 'gia'
    unresolved = []
    spatial = spatial_objects(header, root, unresolved)
    objects, references, issues = [], [], []
    seen = set()

    def obj(kind, ident, name='', scope=(), **detail):
        target = key(namespace, kind, *scope, ident)
        if target in seen:
            issues.append({'error': 'duplicate scene identity', 'key': target})
        seen.add(target)
        objects.append({'key': target, 'artifact': namespace, 'kind': kind, 'id': ident,
                        'name': name, 'scope': list(scope), **detail})
        return target

    def link(source, target, relation, **location):
        references.append({'source': source, 'target': target, 'relation': relation, 'location': location})

    digest = sha(data)
    document = obj('document', 'root', fmt, sha256=digest)
    if fmt == 'gia':
        for (_, ident), detail in spatial.items():
            obj('gia_resource', ident, detail['name'], scope=(1,), spatial=detail)
    else:
        try:
            for graph_kind, raw in graph_records(data):
                locator = get(raw, 1, default=b'')
                identity = ref(locator)
                obj('graph', identity, get(raw, 2, default=b'').decode('utf-8'), (graph_kind,),
                    native_category=get(locator, 2, 0))
            for gid in graph_library_ids(root):
                link(document, key(namespace, 'graph', 'ordinary', gid), 'graph_library')
        except ValueError as exc:
            unresolved.append({'section': 10, 'error': str(exc)})
        for section, kind in ((4, 'template'), (5, 'entity')):
            records = (raw for group in vals(root, section) for raw in vals(fields(group), 1))
            for ident, raw, error in identified_records(records):
                if error:
                    issues.append({'section': section, 'id': ident, 'error': error})
                    continue
                detail = spatial.get((kind, ident))
                name = detail['name'] if detail else ''
                if not detail:
                    try:
                        label = typed_record(raw, 6 if section == 4 else 5, 1)
                        name = get(get(label or b'', 11, default=b''), 1, default=b'').decode('utf-8')
                    except ValueError as exc:
                        unresolved.append({'section': section, 'id': ident, 'error': str(exc)})
                source = obj(kind, ident, name, section=section, spatial=detail)
                for part in (detail or {}).get('decorations', []):
                    target = obj('decoration', part['id'], part['name'], (kind, ident),
                                 section=27, owner_section=section, owner_id=ident, spatial=part)
                    link(target, source, 'decoration_owner')
                if section == 5:
                    try:
                        for locator in vals(fields(raw), 2):
                            target_id, category = get(locator, 1, 0), get(locator, 2, 0, 0)
                            if not target_id or category not in (0, 1):
                                unresolved.append({'key': source, 'error': 'uncalibrated template locator', 'category': category})
                                continue
                            if category == 0:
                                link(source, key(namespace, 'template', target_id), 'entity_template')
                            else:
                                target = key(namespace, 'platform_template', target_id)
                                if target not in seen:
                                    obj('platform_template', target_id, external=True, resource_verified=False)
                                link(source, target, 'platform_template')
                    except ValueError as exc:
                        unresolved.append({'key': source, 'error': str(exc)})
                try:
                    for gid in entity_graph_ids(raw):
                        link(source, key(namespace, 'graph', 'ordinary', gid), 'graph_mount')
                except ValueError as exc:
                    unresolved.append({'key': source, 'error': str(exc)})
        for edge in references:
            if edge['target'] not in seen:
                unresolved.append({'error': 'scene reference target absent', **edge})
    return {'schema': 2, 'scope': 'scene', 'status': 'failed' if issues else 'passed',
            'artifacts': {namespace: {'format': fmt, 'sha256': digest}}, 'objects': objects,
            'script_mappings': [], 'references': references, 'issues': issues, 'unresolved': unresolved,
            'checks': {'scene_index': {'status': 'failed' if issues else 'passed'},
                       'spatial_coverage': {'status': 'not_checked' if unresolved else 'passed',
                                            'unresolved': len(unresolved)},
                       'graph_audit': {'status': 'not_checked'}},
            'complete_reference_index': False, 'unindexed': ['graph_ports', 'client_bindings', 'arbitrary_component_payloads'],
            'editor': 'not_checked', 'host': 'not_checked'}


def inspect(path,level=None,*,scope=None):
    path=Path(path).resolve()
    if scope not in (None, 'scene', 'gameplay'):
        raise ValueError('Unknown project inspection scope')
    if path.suffix.lower()in('.gil','.gia'):
        reader = build_scene if scope == 'scene' else build
        if scope == 'gameplay':
            from native_gameplay_index import build_gameplay
            reader = build_gameplay
        report=reader(path.read_bytes());report['inputs']={str(path):report['artifacts']['level']['sha256']};return report
    if scope:
        raise ValueError(f'{scope} scope requires a native file')
    spec=read_json(path);schema(spec,('schema','artifacts','required_references'),('schema','artifacts'))
    if not isinstance(spec['artifacts'],list)or not spec['artifacts']:raise ValueError('Explicit nonempty project artifacts required')
    reports=[];seen=set();inputs={str(path):sha(path.read_bytes())}
    for entry in spec['artifacts']:
        schema(entry,('name','source','sha256'),('name','source'))
        name=entry['name']
        if not isinstance(name,str)or not name.strip()or name in seen:raise ValueError('Unique artifact names required')
        if not isinstance(entry['source'],str)or not entry['source']:raise ValueError('Artifact source path required')
        seen.add(name)
        if entry['source']=='@level':
            if level is None:raise ValueError('@level requires final production artifact')
            raw=level;source=None
        else:
            source=resolve(path.parent,entry['source']);raw=source.read_bytes()
        digest=sha(raw)
        if 'sha256'in entry and entry['sha256']!=digest:raise ValueError('Project artifact digest changed: '+name)
        if source is not None:inputs[str(source)]=digest
        reports.append(build(raw,name))
    result={**reports[0],'artifacts':{k:v for r in reports for k,v in r['artifacts'].items()},'inputs':inputs}
    for field in('objects','script_mappings','references','graph_variable_accesses','issues','unresolved'):result[field]=[v for r in reports for v in r[field]]
    requirements=spec.get('required_references',[])
    if not isinstance(requirements,list):raise ValueError('required_references must be a list')
    for requirement in requirements:
        schema(requirement,('source','target','relation'),('source','target','relation'))
        select(result,{'key':requirement['source']});select(result,{'key':requirement['target']})
        hits=[r for r in result['references']if all(r[k]==v for k,v in requirement.items())]
        if len(hits)!=1:result['issues'].append({'error':'required reference missing or ambiguous',**requirement,'count':len(hits)})
    result['status']='failed'if result['issues']else'not_checked'if result['unresolved']else'passed'
    return result


def select(report,selector):
    schema(selector,('key','kind','name','id'))
    if not selector:raise ValueError('Explicit object selector required')
    if any(not isinstance(v,str)or not v for k,v in selector.items()if k!='id')or 'id'in selector and type(selector['id'])not in(int,str):
        raise ValueError('Object selector requires nonempty strings and integer/string ID')
    matches=[o for o in report['objects']if all(o.get(k)==v for k,v in selector.items())]
    if len(matches)!=1:
        candidates=[o['key'] for o in matches]
        raise DiagnosticError('project.selector_ambiguous' if candidates else 'project.selector_missing',
                              'Object selector must be unique: '+json.dumps({'selector':selector,'matches':candidates},ensure_ascii=False),
                              phase='project_inspect', expected=1, actual=len(candidates), selector=selector, candidates=candidates)
    return matches[0]


def consumers(report,selector,transitive=False):
    target=select(report,selector);incoming=defaultdict(list)
    for r in report['references']:incoming[r['target']].append(r)
    seen={target['key']};pending=deque([target['key']]);edges=[];keys=set()
    while pending:
        for edge in incoming[pending.popleft()]:
            edges.append(edge);source=edge['source']
            if source!=target['key']:keys.add(source)
            if transitive and source not in seen:seen.add(source);pending.append(source)
    dependencies = [edge for edge in report['references'] if edge['source']==target['key']]
    dependency_keys = {edge['target'] for edge in dependencies}
    detail = {}
    if report.get('scope') in ('scene','gameplay'):
        related = [item for item in report['unresolved'] if item.get('key',item.get('source'))==target['key'] or
                   (target.get('section') is not None and item.get('section')==target['section'] and item.get('id')==target['id'])]
        detail = {'scope':report['scope'],'checks':report['checks'],'unresolved':related}
        if report['scope']=='gameplay':
            detail['diagnostics']=[issue for issue in report['issues']
                                   if target['key'] in (issue.get('object'),issue.get('target'))]
    return {'schema':2,'status':report['status'],'target':target,'transitive':transitive,'consumers':[o for o in report['objects']if o['key']in keys],
            'dependencies':[o for o in report['objects']if o['key']in dependency_keys],'dependency_references':dependencies,
            'references':edges,'complete_reference_index':report['complete_reference_index'],'unindexed':report['unindexed'],
            'artifacts':report['artifacts'],'inputs':report.get('inputs',{}),'script_mappings':report['script_mappings'],
            'editor':'not_checked','host':'not_checked',**detail}


def inspect_summary(report):
    if 'target' in report:
        return report
    counts = Counter(row['kind'] for row in report['objects'])
    return {k: report[k] for k in ('schema','status','scope','artifacts','inputs','script_mappings','editor','host') if k in report} | {
        'object_counts': dict(counts), 'reference_count': len(report['references']),
        'checks': report.get('checks', {'project_references': report['status']}),
        'diagnostics': report['issues'] + report['unresolved'], 'complete_reference_index': False}


def main(argv=None):
    parser=argparse.ArgumentParser();commands=parser.add_subparsers(dest='operation',required=True)
    for name in('inspect','check','consumers'):
        command=commands.add_parser(name);command.add_argument('input')
        if name in ('inspect','consumers'):
            command.add_argument('--scope',choices=['scene','gameplay'])
            command.add_argument('--summary',action='store_true')
            command.add_argument('--out')
            choice=command.add_mutually_exclusive_group(required=name=='consumers')
            choice.add_argument('--key');choice.add_argument('--name');choice.add_argument('--id',type=int)
            command.add_argument('--kind');command.add_argument('--transitive',action='store_true')
    args=parser.parse_args(argv);result=inspect(args.input,scope=getattr(args,'scope',None))
    selector = {k:getattr(args,k) for k in ('key','kind','name','id') if getattr(args,k,None) is not None}
    if selector:
        result=consumers(result,selector,args.transitive)
    elif getattr(args,'transitive',False):
        parser.error('--transitive requires a selector')
    if output := getattr(args,'out',None):
        with Path(output).open('x',encoding='utf-8') as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2)
    if getattr(args,'summary',False):
        result=inspect_summary(result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='passed'else 2


if __name__=='__main__':raise SystemExit(main())
