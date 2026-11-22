"""Compile explicit replacements in isolation while preserving live graph identities."""
from pathlib import Path
import re,shutil,tempfile
from authoring_io import *
from native_core import apply,model,get,put,rewrite,audit,register_definitions,require_mounts
from level_inventory import fields,container
from level_authoring import set_section

def build(spec_path,out_dir):
    from node_build import build as legacy_build
    from native_bindings import bindings_for_gil, read_bindings
    path=Path(spec_path).resolve();base=path.parent
    spec_bytes=path.read_bytes();job=json.loads(spec_bytes.decode('utf-8-sig'))
    schema(job,('schema','graphs','formats','base_gil','project_resources','include_sections','allowed_top_level_fields','mounts','required_mounts','max_stored_nodes','replace_graphs','strict_audit','struct_bindings','graph_ids','export_epoch','bindings'),('graphs','base_gil','allowed_top_level_fields'))
    mounts=job.get('mounts',[])
    if not isinstance(mounts,list):raise ValueError('Graph mounts must be a list')
    for item in mounts:
        schema(item,('graph_name','entity_id','section'),('graph_name','entity_id','section'))
        if type(item['section']) is not int or item['section'] not in (4,5) or type(item['entity_id']) is not int:
            raise ValueError('Graph mounts require a native entity identity in section 4 or 5')
    epoch=job.get('export_epoch',0)
    if type(epoch)!=int or not 0<=epoch<2**31:raise ValueError('export_epoch must be a nonnegative 31-bit integer')
    original_path=resolve(base,job['base_gil']);original=original_path.read_bytes()
    inputs=ProductionInputs({str(path):sha(spec_bytes),str(original_path):sha(original)})
    bindings=None
    if job.get('bindings'):
        binding_path=resolve(base,job['bindings'])
        bindings,binding_digest=read_bindings(binding_path,original)
        inputs.bind(binding_path,binding_digest,'graph_bindings')
    before=model(original);selected=[]
    for target in job.get('replace_graphs',[]):
        matches=[g for g in before['graphs']if g['id']==target['graph_id']and g['name']==target['graph_name']]
        if len(matches)!=1 or any(g['id']==target['graph_id']for g in selected):raise ValueError('Replacement ID/name must match exactly once')
        selected.append(matches[0])
    section=get(original[20:-4],10,default=b'')
    stripped=b''.join(raw for n,w,v,raw in fields(section)if not(n==1 and w==2 and any(get(v,1)==g['raw']for g in selected)))
    with tempfile.TemporaryDirectory(prefix='qianxing-replace-')as td:
        work=Path(td);(work/'base.gil').write_bytes(register_definitions(set_section(original,10,stripped)))
        legacy={k:v for k,v in job.items()if k not in ('replace_graphs','strict_audit','struct_bindings','graph_ids','export_epoch','mounts','bindings')};legacy['schema']=1;legacy['base_gil']=str(work/'base.gil');legacy['formats']=['gia','gil'];legacy['required_mounts']=[]
        # Upstream signal/struct import normalizes UI metadata even with UI skipped.
        # Permit this only in the disposable intermediate; restore the original UI
        # section before applying the user's actual protected-field contract.
        legacy['allowed_top_level_fields']=list(dict.fromkeys(job['allowed_top_level_fields']+[9]))
        for g in legacy['graphs']:g['source']=str(resolve(base,g['source']))
        if legacy.get('project_resources'):legacy['project_resources']=str(resolve(base,legacy['project_resources']))
        write_json(work/'job.json',legacy)
        legacy_build(work/'job.json',work/'compiled',preserve_container_order=True,
                     structure_bindings=job.get('struct_bindings',()),resolved_bindings=bindings)
        # Only newly exported GIA file-path tags contain the backend wall clock.
        # Bind that presentation timestamp to a declared reproducible epoch;
        # preserve UID, native graph ID, file name, payload and every baseline byte.
        export_tags=[]
        from level_authoring import pack
        for p in (work/'compiled/gia').glob('*.gia'):
            raw=p.read_bytes();header,root=container(raw);tag=get(raw[20:-4],3)
            if tag is None:raise ValueError('Generated GIA export tag absent')
            match=re.fullmatch(rb'(\d+)-(\d+)-(\d+)-(.*)',tag)
            if match is None:raise ValueError('Unknown GIA export tag shape')
            normalized=match[1]+b'-'+str(epoch).encode()+b'-'+match[3]+b'-'+match[4]
            p.write_bytes(pack(put(raw[20:-4],3,normalized),header[1:4]));export_tags.append({'file':p.name,'source_tag':tag.decode('utf-8'),'export_tag':normalized.decode('utf-8')})
        result=(work/'compiled/level.gil').read_bytes();section=get(result[20:-4],10,default=b'');current=model(result)
        if 9 not in job['allowed_top_level_fields']:
            original_ui=[r for n,w,v,r in container(original)[1]if n==9];inserted=False;rows=[]
            for n,w,v,r in container(result)[1]:
                if n==9:
                    if not inserted:rows.extend(original_ui);inserted=True
                else:rows.append(r)
            from level_authoring import pack
            result=pack(b''.join(rows),container(result)[0][1:4])
        for old in selected:
            hits=[g for g in current['graphs']if g['name']==old['name']]
            if len(hits)!=1:raise ValueError('Compiled replacement missing')
            generated=hits[0]
            if generated['id']!=old['id']and any(g['id']==old['id']and g['name']!=old['name']for g in current['graphs']):raise ValueError('Replacement identity collision')
            fixed=put(generated['raw'],1,get(old['raw'],1));section=rewrite(section,1,lambda w:put(w,1,fixed)if get(w,1)==generated['raw']else w)
        result=set_section(result,10,section)
        for name,gid in job.get('graph_ids',{}).items():
            current=model(result);hits=[g for g in current['graphs']if g['name']==name]
            if type(gid)!=int or not 2**30<=gid<2**31 or len(hits)!=1 or any(g['id']==gid and g['name']!=name for g in current['graphs']):raise ValueError('Requested graph identity collision')
            if any(g['name']==name and g['id']!=gid for g in before['graphs']):raise ValueError('Existing graph identity cannot be changed')
            old=hits[0]['raw'];new=put(old,1,put(get(old,1),5,gid,0));section=get(result[20:-4],10,default=b'')
            result=set_section(result,10,rewrite(section,1,lambda w:put(w,1,new)if get(w,1)==old else w))
            old_id=hits[0]['id']
            if old_id!=gid:
                # The compiler has already registered its allocated graph ID.
                # Rebinding a new graph must carry its calibrated library and
                # mount references; the caller's protected-field check remains
                # authoritative for every changed section.
                library=get(result[20:-4],6)
                if library is not None:
                    library=rewrite(library,1,lambda e:rewrite(e,3,lambda group:rewrite(group,5,lambda r:put(r,2,gid,0)if get(r,2,0)==old_id else r))if get(e,1,0)==4 else e)
                    result=set_section(result,6,library)
                category=get(get(old,1),2,0)
                from level_inventory import graph_component_field
                for section_id in(4,5):
                    entities=get(result[20:-4],section_id)
                    if entities is None:continue
                    def mount_entry(entry):
                        r=get(entry,1,default=b'')
                        return put(entry,1,put(r,2,gid,0))if get(r,2,0)==old_id and get(r,3,0,category)==category else entry
                    entities=rewrite(entities,1,lambda e:rewrite(e,graph_component_field(e,section_id),lambda c:rewrite(c,13,lambda group:rewrite(group,1,mount_entry))if get(c,1,0)==3 else c))
                    result=set_section(result,section_id,entities)
        if job.get('struct_bindings'):
            from native_core import bind_structures
            result=bind_structures(result,job['struct_bindings'])
        if mounts:
            current=model(result)
            operations=[]
            for item in mounts:
                graphs=[g for g in current['graphs'] if g['name']==item['graph_name']]
                if len(graphs)!=1 or get(get(graphs[0]['raw'],1),2,0)!=20000:
                    raise ValueError('Expected one ordinary server graph to mount: '+repr(item['graph_name']))
                operations.append({'op':'mount','section':item['section'],'entity_id':item['entity_id'],
                                   'graph_id':graphs[0]['id']})
            result,_=apply(result,{'schema':2,'base_sha256':sha(result),'operations':operations,
                                   'allowed_top_level_fields':job['allowed_top_level_fields']},base)
        after=model(result)
        for old in before['graphs']:
            matches=[g for g in after['graphs']if g['id']==old['id']]
            if len(matches)!=1 or old not in selected and matches[0]['raw']!=old['raw']:raise ValueError('Unrelated graph changed')
        protected=lambda b:[r for n,w,v,r in container(b)[1]if n not in job['allowed_top_level_fields']]
        if protected(original)!=protected(result):raise ValueError('Protected fields changed')
        final=audit(result,job.get('strict_audit',True))
        if final['status']!='passed':raise ValueError('Final native audit: '+canonical(final))
        required_mounts=job.get('required_mounts',[])+mounts
        require_mounts(after,required_mounts)
        compiler=read_json(work/'compiled/build-report.json')
        inputs.merge({p:h for p,h in compiler['inputs_sha256'].items() if not Path(p).is_relative_to(work)},'graphs')
        with output_directory(out_dir)as stage:
            shutil.copytree(work/'compiled',stage,dirs_exist_ok=True);(stage/'level.gil').write_bytes(result)
            report={'schema':2,'audit':final,'replaced_graphs':[g['id']for g in selected],'export_epoch':epoch,'generated_gia_tags':export_tags,'protected_fields_unchanged':True,'mount_contract_checked':bool(required_mounts),'gil':{'required_mounts_verified':len(required_mounts)},'host_tested':False}
            write_json(stage/'compiler-report.json',compiler)
            files={name:sha_file(stage/name) for name in compiler['files_sha256']}
            if bindings is not None:
                report['binding_identity']='passed'
                if bindings.ids:
                    write_json(stage/'bindings.json',bindings_for_gil(result,bindings))
                    files['bindings.json']=sha_file(stage/'bindings.json')
            write_json(stage/'build-report.json',{**compiler,'schema':2,'inputs_sha256':inputs,'artifact_scope':'Current build artifacts; upstream pre-binding evidence is compiler-report.json','compiler_report':'compiler-report.json','final_audit':final,'export_epoch':epoch,'mount_contract_checked':bool(required_mounts),'files_sha256':files,'gil':{**(compiler.get('gil')or{}),'required_mounts_verified':len(required_mounts)},**({'binding_identity':report['binding_identity']} if bindings is not None else {})})
            write_json(stage/'replacement-report.json',report);finish(stage,inputs,kind='native-build');return report
