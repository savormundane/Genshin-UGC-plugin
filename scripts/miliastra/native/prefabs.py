"""Author ordinary object templates and placements from calibrated native model records."""
from authoring_io import resolve, schema
from level_authoring import integer, msg, set_section, vi
from level_inventory import container, entity_graph_ids, fields, unique, vals
from miliastra.native.core import get, replace_message
from miliastra.native.scene import GIL_HEADER, TRS, is_object_id, ordinary_object, placed_details, read_templates, typed_record
from miliastra.native.scene_edits import (append_decorations, append_library_entries, DECORATION_END, DECORATION_START,
                                decoration_links, describe_decoration, next_object_ids, patch_fields,
                                rename_transform_object, select_record)

OBJECT_CREATION = {'place_model_instances','create_object_templates','instantiate_object_templates'}


def model_witness(row):
    """Accept the standard platform object layout, with portable defaults only."""
    record = ordinary_object(row)
    rows = fields(row)
    if not record or not 0 < record['template_id'] < 0x40000000 or any(
            (n,w) not in ((1,0),(2,2),(5,2),(6,2),(7,2),(8,0)) for n,w,_,_ in rows):
        raise ValueError('Model witness must be an ordinary editor-placed platform object')
    allowed = {5:{1,13,14,19,20,38,40,52,61,62},6:{1,2,3,4,5,6,7,8,11,12,16,17,19},
               7:{1,3,6,14,18,19}}
    for field, kinds in allowed.items():
        actual = [get(part,1,0) for part in vals(rows,field)]
        if len(set(actual))!=len(actual) or set(actual)-kinds:
            raise ValueError('Model witness has components outside the ordinary object format')
    reference=get(row,2,default=b'')
    if any((n,w) not in ((1,0),(2,0)) for n,w,_,_ in fields(reference)):
        raise ValueError('Model witness locator contains a project dependency')
    model = typed_record(row,6,2)
    graph = typed_record(row,6,3)
    variables = typed_record(row,7,1)
    if (decoration_links(row,5)[1] or (graph is not None and (get(graph,13,default=b'')
            or any((n,w) not in ((1,0),(13,2)) for n,w,_,_ in fields(graph))))
            or get(model or b'',12,default=b'')
            or (variables is not None and get(variables,11,default=b''))
            or any(w==2 and vi(record['record_id']) in value for _,w,value,_ in rows)):
        raise ValueError('Model witness contains instance-specific dependencies')
    return record


def author_objects(data, op, base):
    """Create platform instances, dynamic templates, or instances of project templates."""
    kind = op['op']
    creating_templates = kind == 'create_object_templates'
    instantiating = kind == 'instantiate_object_templates'
    key_field = 'templates' if creating_templates else 'instances'
    if instantiating:
        schema(op, ('op', key_field), (key_field,))
        sample = data
    else:
        schema(op, ('op', 'source', 'version', 'mode', key_field), ('source','version','mode',key_field))
        from scene_authoring import MODE, VERSION
        if (op['version'],op['mode'])!=(VERSION,MODE):
            raise ValueError('Native object authoring uses a 7.2 beyond model witness')
        sample = resolve(base,op['source']).read_bytes()
    header,source_root = container(sample)
    if header[1:4]!=GIL_HEADER:
        raise ValueError('Native object authoring requires a GIL witness')
    choices=op[key_field]
    if not isinstance(choices,list) or not choices:
        raise ValueError('Provide at least one native object')
    _,root=container(data)
    available=next_object_ids(data,root)
    source_section=unique(source_root,4 if instantiating else 5,default=b'')
    templates=read_templates(root)
    created=[]
    keys=set()
    records=[]
    parts_by_owner={}
    decoration_section=unique(root,27,default=b'')
    decoration_records=fields(decoration_section) if instantiating else []
    occupied_decoration_ids={get(x,1,0) for field in (1,2) for x in vals(decoration_records,field)}
    next_decoration=max((i for i in occupied_decoration_ids if i is not None and DECORATION_START<=i<=DECORATION_END),
                        default=DECORATION_START-1)+1
    placed_parts=[]
    for item in choices:
        selector='template_id' if instantiating else 'model_entity_id'
        optional=('scale','parts') if creating_templates else TRS
        required=('key','name',selector) if creating_templates else ('key','name',selector,'position_m')
        schema(item,('key','name',selector,*optional),required)
        key=item['key']
        if not isinstance(key,str) or not key.strip() or key in keys:
            raise ValueError('Object keys must be unique nonempty strings')
        keys.add(key)
        if not is_object_id(item[selector]):
            raise ValueError('Ordinary object identity required')
        original=select_record(source_section,1,item[selector],'Model witness' if not instantiating else 'Object template')
        ident=next(available,None)
        if ident is None:
            raise ValueError('Ordinary object ID range exhausted')
        if instantiating:
            if item[selector] not in templates or any((n,w) not in ((1,0),(2,0),(6,2),(7,2),(8,2),(10,0)) for n,w,_,_ in fields(original)):
                raise ValueError('Select an ordinary object template with the calibrated component layout')
            model=get(original,2,0)
            prop, part_ids=decoration_links(original,4)
            new_ids=[]
            for part_id in part_ids:
                source_part=select_record(decoration_section,1,part_id,'Template decoration')
                detail=describe_decoration(source_part)
                if (detail['owner_id']!=item[selector] or get(source_part,11)!=b'' or get(source_part,12) is not None):
                    raise ValueError('Uncalibrated template decoration dependency')
                if next_decoration>DECORATION_END:
                    raise ValueError('Decoration ID range exhausted')
                owner=typed_record(source_part,4,40,strict=True)
                link=patch_fields(get(owner,50),{502:(0,ident)})
                part=replace_message(source_part,4,owner,patch_fields(owner,{50:(2,link)}))
                part=patch_fields(part,{1:(0,next_decoration),3:(0,None),11:(2,None),12:(2,integer(1,part_id))})
                placed_parts.append(msg(2,part))
                new_ids.append(next_decoration)
                next_decoration+=1
            pieces=[]
            for n,w,body,_ in fields(original):
                if w!=2 or n not in (6,7,8):
                    continue
                block_type=get(body,1,0)
                if (n,block_type)==(6,40):
                    linked=msg(501,b''.join(vi(i) for i in new_ids)) if new_ids else b''
                    body=patch_fields(prop,{50:(2,linked)})
                if (n,block_type)==(8,1):
                    body=integer(1,1)+integer(2,1)+msg(11)
                pieces.append(msg(n-1,body))
            pieces.extend(msg(5,integer(1,k)+msg(k+10)) for k in (19,52))
            raw=integer(1,ident)+msg(2,integer(1,item[selector]))+b''.join(pieces)+integer(8,model)
            raw=rename_transform_object(raw,item['name'],item)
        else:
            verified=model_witness(original)
            model=verified['template_id']
            if creating_templates:
                if verified['static'] or typed_record(original,6,3) is None:
                    raise ValueError('Creating a dynamic template requires a dynamic platform model witness')
                pose={**item,'position_m':[0,0,0],'rotation_deg':[0,0,0]}
                source=rename_transform_object(original,item['name'],pose)
                pieces=[]
                for n,w,body,_ in fields(source):
                    if w!=2 or n not in (5,6,7) or n==5 and get(body,1,0) in (19,20,52):
                        continue
                    if (n,get(body,1,0))==(6,4):
                        body=patch_fields(body,{14:(2,integer(1,1))})
                    pieces.append(msg(n+1,body))
                raw=integer(1,ident)+integer(2,model)+b''.join(pieces)+integer(10,1)
                if 'parts' in item:
                    parts_by_owner[ident]=item['parts']
            else:
                raw=patch_fields(rename_transform_object(original,item['name'],item),{1:(0,ident)})
        records.append(msg(1,raw))
        entry={'key':key,'name':item['name'],'model_id':model}
        if creating_templates:
            entry['template_id']=ident
        else:
            entry.update(entity_id=ident,graph_ids=list(entity_graph_ids(raw)),**placed_details(raw,templates))
            if instantiating and new_ids:
                entry['decoration_ids']=new_ids
        created.append(entry)
    section,tab,code,id_field=(4,6,100,'template_id') if creating_templates else (5,3,200,'entity_id')
    library=unique(root,6,default=b'')
    output=set_section(data,section,unique(root,section,default=b'')+b''.join(records))
    output=set_section(output,6,append_library_entries(library,tab,code,[r[id_field] for r in created]))
    if placed_parts:
        output=set_section(output,27,decoration_section+b''.join(placed_parts))
    if parts_by_owner:
        for entry in created:
            ident=entry['template_id']
            if ident in parts_by_owner:
                output,parts=append_decorations(output,{'op':'append_decorations','section':4,
                                                         'entity_id':ident,'parts':parts_by_owner[ident]})
                entry['parts']=parts['parts']
    return output,{key_field:created}
