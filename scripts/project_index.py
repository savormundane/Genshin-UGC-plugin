"""Read-only engineering identities and calibrated dependency/consumer queries."""
from pathlib import Path
from collections import Counter,defaultdict,deque
from urllib.parse import quote
import argparse,json
from authoring_io import sha,read_json,schema,resolve
from level_inventory import container,fields,vals,unique
from level_authoring import inspect_bindings,ui_records,stream
from native_core import model,audit,get,ref,slot,definition_id,node_catalog


def key(*parts):return '/'.join(quote(str(p),safe='')for p in parts)


def build(data,namespace='level'):
    m=model(data);validation=audit(data);_,root=container(data)
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
    from native_signals import declarations
    from native_ports import resolve_dynamic
    signal_records=declarations(m)if m['format']=='gia'else{}
    roles={i:(r['name'],r['role'])for i,r in signal_records.items()}
    for s in m['signals']:
        for role in(1,2,7,9):
            locator=get(s,role)
            if locator:roles[ref(locator)]=(get(s,3,default=b'').decode('utf-8'),role)
    resolved_graphs={};connections={}
    # Concrete builtin variants have their own IDs; they remain external definitions.
    builtin_ids=set(builtin)|{v['ConcreteId']for item in builtin.values()for v in item.get('TypeMappings',[])}
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
                if descriptor:node_type(source,ref(descriptor),relation)
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
    for entity in m['entities']:
        obj('template'if entity['section']==4 else'entity',entity['entity_id'])
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
    if m['format']=='gia':
        names=set()
        for ident,s in signal_records.items():
            if s['name']not in names:obj('signal',s['name'],s['name']);names.add(s['name'])
            source=key(namespace,'definition',ident);link(source,key(namespace,'signal',s['name']),'signal_contract',role=s['role'])
            for role,peer in s['peers'].items():
                if peer:link(source,key(namespace,'definition',ref(peer)),'signal_peer',role=role)
        for resource in m['resources']:
            source=obj('gia_resource',resource['id'],'',(resource['class'],))
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
    return {'schema':2,'status':'failed'if issues else'not_checked'if unknown else'passed','artifacts':{namespace:{'format':m['format'],'sha256':sha(data)}},
            'objects':objects,'references':references,'graph_variable_accesses':variable_accesses,'issues':issues,'unresolved':unknown,'scope':'calibrated native and client object references',
            'complete_reference_index':False,'unindexed':['arbitrary_component_payloads','custom_variable_access_and_literal_targets','graph_variable_dynamic_access_and_overrides','implicit_graph_structure_identity','untyped_numeric_constants','dynamic_Lua_identifiers','platform_resource_catalogue'],
            'editor':'not_checked','host':'not_checked'}


def inspect(path,level=None):
    path=Path(path).resolve()
    if path.suffix.lower()in('.gil','.gia'):
        report=build(path.read_bytes());report['inputs']={str(path):report['artifacts']['level']['sha256']};return report
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
    for field in('objects','references','graph_variable_accesses','issues','unresolved'):result[field]=[v for r in reports for v in r[field]]
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
    if len(matches)!=1:raise ValueError('Object selector must be unique: '+json.dumps({'selector':selector,'matches':[o['key']for o in matches]},ensure_ascii=False))
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
    return {'schema':2,'status':report['status'],'target':target,'transitive':transitive,'consumers':[o for o in report['objects']if o['key']in keys],
            'references':edges,'complete_reference_index':report['complete_reference_index'],'unindexed':report['unindexed'],
            'artifacts':report['artifacts'],'editor':'not_checked','host':'not_checked'}


def main(argv=None):
    parser=argparse.ArgumentParser();commands=parser.add_subparsers(dest='operation',required=True)
    for name in('inspect','check','consumers'):
        command=commands.add_parser(name);command.add_argument('input')
        if name=='consumers':
            choice=command.add_mutually_exclusive_group(required=True)
            choice.add_argument('--key');choice.add_argument('--name');choice.add_argument('--id',type=int)
            command.add_argument('--kind');command.add_argument('--transitive',action='store_true')
    args=parser.parse_args(argv);result=inspect(args.input)
    if args.operation=='consumers':result=consumers(result,{k:getattr(args,k)for k in('key','kind','name','id')if getattr(args,k)is not None},args.transitive)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='passed'else 2


if __name__=='__main__':raise SystemExit(main())
