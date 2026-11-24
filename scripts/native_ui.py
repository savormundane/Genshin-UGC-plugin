"""Calibrated fixed-anchor RectTransform layout with independent wire readback."""
from pathlib import Path
import argparse,json,math,struct
from authoring_io import schema,sha,read_json,output_directory,finish,write_json
from level_inventory import calibrated_container,fields,vals,container
from level_authoring import msg,flt,set_section,inspect_bindings
from native_core import get,put


def layout(data,spec):
    schema(spec,('schema','base_sha256','canvas','controls'),('base_sha256','canvas','controls'))
    if sha(data)!=spec['base_sha256']:raise ValueError('UI base hash mismatch')
    calibrated_container(data)
    def numbers(value,count,label):
        if not isinstance(value,list)or len(value)!=count or any(type(v)not in(int,float)or not math.isfinite(v)or abs(v)>1e9 for v in value):raise ValueError('Invalid '+label)
        return value
    if not isinstance(spec['canvas'],dict)or set(spec['canvas'])!={'0','1','2','3'}:raise ValueError('Explicit canvas sizes required for all four states')
    for size in spec['canvas'].values():
        if any(v<=0 for v in numbers(size,2,'canvas')):raise ValueError('Canvas dimensions must be positive')
    if not isinstance(spec['controls'],list)or not spec['controls']:raise ValueError('UI controls required')
    section=get(data[20:-4],9,default=b'');records=vals(fields(section),502);changes={};report=[];parents={}
    binding=inspect_bindings(data)
    if binding['diagnostics']:raise ValueError('UI input bindings invalid')
    def rewrite(raw,field,fn):
        chunks=[]
        for n,w,v,r in fields(raw):
            changed=fn(v)if (n,w)==(field,2)else v
            chunks.append(msg(n,changed)if changed!=v else r)
        return b''.join(chunks)
    def vector(x,y):return flt(501,x)+flt(502,y)
    def readvec(raw):return [struct.unpack('<f',get(raw,k,5,b'\0'*4))[0]for k in(501,502)]
    for item in spec['controls']:
        schema(item,('guid','template','states','allow_outside','parent'),('states',))
        if ('guid'in item)==('template'in item):raise ValueError('Choose one UI guid or template name')
        if 'parent'in item and('guid'not in item or type(item['parent'])is not int or item['parent']<=0):raise ValueError('Parent verification requires explicit child and parent GUIDs')
        if 'allow_outside'in item and type(item['allow_outside'])is not bool:raise ValueError('allow_outside must be boolean')
        if 'guid'in item:
            if type(item['guid'])is not int:raise ValueError('UI GUID must be integer')
            targets=[item['guid']]
        else:
            matches=[t for t in binding['templates']if t['name']==item['template']]
            if len(matches)!=1:raise ValueError('UI template name must be unique')
            targets=[matches[0]['template_guid'],matches[0]['entry_guid']]
        states=item['states']
        if not isinstance(states,dict)or not states or set(states)-{'0','1','2','3'}:raise ValueError('Explicit valid state selections required')
        expected={}
        for state,config in states.items():
            schema(config,('rect','anchor','pivot','scale'),('rect','anchor','pivot'))
            x,y,w,h=numbers(config['rect'],4,'rect');anchor=numbers(config['anchor'],2,'anchor');pivot=numbers(config['pivot'],2,'pivot')
            if w<=0 or h<=0 or any(not 0<=v<=1 for v in anchor+pivot):raise ValueError('Invalid size/anchor/pivot range')
            scale=numbers(config.get('scale',[1,1]),2,'scale')
            if any(v<=0 for v in scale):raise ValueError('UI scale must be positive')
            visible=[x+pivot[0]*w*(1-scale[0]),y+(1-pivot[1])*h*(1-scale[1]),w*scale[0],h*scale[1]]
            cw,ch=spec['canvas'][state]
            vx,vy,vw,vh=visible
            outside=vx<0 or vy<0 or vx+vw>cw or vy+vh>ch
            if outside and not item.get('allow_outside',False):raise ValueError('UI rectangle outside declared canvas')
            px=x+pivot[0]*w;py=ch-y-(1-pivot[1])*h
            expected[int(state)]={'anchor':anchor,'pivot':pivot,'position':[px-anchor[0]*cw,py-anchor[1]*ch],'size':[w,h],'rect':[x,y,w,h],'outside':outside,'scale':scale,'scale_explicit':'scale'in config,'visible_rect':visible}
        for guid in targets:
            if guid in changes:raise ValueError('UI control selected more than once')
            if 'parent'in item:parents[guid]=item['parent']
            selected=[r for r in records if get(r,501,0)==guid]
            if len(selected)!=1:raise ValueError('UI GUID must select exactly one control')
            control=selected[0];components=[c for c in vals(fields(control),505)if get(c,501,0)==1 and get(c,502,0)==12]
            if len(components)!=1:raise ValueError('Calibrated RectTransform component required')
            component=components[0];overrides=[o for o in vals(fields(component),503)if get(o,501,0)==4]
            if len(overrides)!=1:raise ValueError('Unique RectTransform override required')
            override=overrides[0];wrapper=get(override,13,default=b'');state_data=get(wrapper,12,default=b'')
            ids=[get(s,501,0,0)for s in vals(fields(state_data),501)]
            if len(ids)!=len(set(ids))or set(expected)-set(ids):raise ValueError('Missing/duplicate RectTransform state')
            def patch_state(raw):
                state=get(raw,501,0,0)
                if state not in expected:return raw
                transform=get(raw,502,default=b'');e=expected[state]
                scale=get(transform,501,default=b'')
                prior_scale=[struct.unpack('<f',get(scale,k,5,b'\0'*4))[0]for k in(1,2,3)]
                if prior_scale[2]!=1 or get(transform,508,default=b''):
                    raise ValueError('Depth scale/rotation requires separate calibration')
                if not e['scale_explicit']and prior_scale!=[1,1,1]:raise ValueError('Nonunit scale requires explicit scale configuration')
                if e['scale_explicit']:
                    # Same Vec3 fields used by the bundled UI readable dump.
                    scale=b''.join(r for k,w,v,r in fields(scale)if k not in(1,2))+flt(1,e['scale'][0])+flt(2,e['scale'][1])
                    transform=put(transform,501,scale)
                for field,values in ((502,e['anchor']),(503,e['anchor']),(504,e['position']),(505,e['size']),(506,e['pivot'])):
                    transform=put(transform,field,vector(*values))
                return put(raw,502,transform)
            updated=rewrite(state_data,501,patch_state)
            # Decode the serialized floats, not the source configuration.
            for raw in vals(fields(updated),501):
                state=get(raw,501,0,0)
                if state not in expected:continue
                transform=get(raw,502);a=readvec(get(transform,502));b=readvec(get(transform,503));p=readvec(get(transform,506));pos=readvec(get(transform,504));size=readvec(get(transform,505))
                cw,ch=spec['canvas'][str(state)];rect=[pos[0]+a[0]*cw-p[0]*size[0],ch-(pos[1]+a[1]*ch)-(1-p[1])*size[1],*size]
                if a!=b or any(not math.isclose(v,w,rel_tol=1e-6,abs_tol=1e-4)for v,w in zip(rect,expected[state]['rect'])):raise ValueError('UI float32 readback differs from requested rectangle')
                scale_raw=get(transform,501);scale=[struct.unpack('<f',get(scale_raw,k,5))[0]for k in(1,2)]
                visible=[rect[0]+p[0]*size[0]*(1-scale[0]),rect[1]+(1-p[1])*size[1]*(1-scale[1]),size[0]*scale[0],size[1]*scale[1]]
                if any(not math.isclose(v,w,rel_tol=1e-6,abs_tol=1e-4)for v,w in zip(scale+visible,expected[state]['scale']+expected[state]['visible_rect'])):raise ValueError('UI scale readback differs')
                report.append({'guid':guid,'state':state,'rect':rect,'anchor':a,'pivot':p,'scale':scale,'visible_rect':visible,'outside':expected[state]['outside']})
            changed_override=put(override,13,put(wrapper,12,updated))
            changed_component=rewrite(component,503,lambda o:changed_override if o==override else o)
            changes[guid]=rewrite(control,505,lambda c:changed_component if c==component else c)
    output=set_section(data,9,rewrite(section,502,lambda r:changes.get(get(r,501,0),r)))
    final_records={}
    for record in vals(fields(get(output[20:-4],9)),502):final_records.setdefault(get(record,501,0),[]).append(record)
    for row in report:
        guid=row['guid'];row['parent_frame_verified']=False
        if guid not in parents:continue
        parent=parents[guid];child=final_records[guid][0]
        if get(child,504,0)!=parent:raise ValueError('Declared parent differs from final UI parent')
        visited={guid};current=parent
        while current is not None:
            if current in visited:raise ValueError('UI parent cycle')
            visited.add(current)
            if len(final_records.get(current,[]))!=1:raise ValueError('UI parent missing or ambiguous')
            current=get(final_records[current][0],504,0)
        record=final_records[parent][0]
        components=[c for c in vals(fields(record),505)if get(c,501,0)==1 and get(c,502,0)==12]
        if len(components)!=1:raise ValueError('Parent RectTransform unavailable')
        overrides=[o for o in vals(fields(components[0]),503)if get(o,501,0)==4]
        if len(overrides)!=1:raise ValueError('Parent RectTransform override unavailable')
        states=get(get(overrides[0],13,default=b''),12,default=b'')
        matches=[s for s in vals(fields(states),501)if get(s,501,0,0)==row['state']]
        if len(matches)!=1:raise ValueError('Parent RectTransform state missing or ambiguous')
        transform=get(matches[0],502,default=b'')
        if readvec(get(transform,502,default=b''))!=readvec(get(transform,503,default=b'')):
            raise ValueError('Stretched parent size requires separate calibration')
        size=readvec(get(transform,505,default=b''))
        if any(not math.isfinite(v)or v<=0 for v in size)or any(not math.isclose(v,w,rel_tol=1e-6,abs_tol=1e-4)for v,w in zip(size,spec['canvas'][str(row['state'])])):
            raise ValueError('Declared canvas differs from final parent local size')
        row.update(parent=parent,parent_size=size,parent_frame_verified=True)
    if inspect_bindings(output)['diagnostics']:raise ValueError('UI output binding check failed')
    protected=lambda raw:b''.join(r for n,w,v,r in container(raw)[1]if n!=9)
    if protected(data)!=protected(output):raise ValueError('Protected UI bytes changed')
    return output,{'schema':2,'status':'passed','scope':'fixed_anchor_rectangles_in_declared_canvases','base_sha256':sha(data),'sha256':sha(output),'controls':report,
                   'protected_fields_unchanged':True,'binary_readback':'passed','editor':'not_checked','host':'not_checked',
                   'parent_geometry_verified':False,'parent_frame_verified':all(r['parent_frame_verified']for r in report),
                   'parent_frame_scope':'fixed_anchor_immediate_parent_local_size','canvas_configuration_written':False}


def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    command=sub.add_parser('apply');command.add_argument('input');command.add_argument('spec');command.add_argument('--out',required=True)
    args=parser.parse_args(argv);source=Path(args.input).resolve();config=Path(args.spec).resolve();raw=source.read_bytes()
    inputs={str(source):sha(raw),str(config):sha(config.read_bytes())};changed,report=layout(raw,read_json(config))
    with output_directory(args.out)as stage:
        (stage/'level.gil').write_bytes(changed);write_json(stage/'ui-report.json',report);finish(stage,inputs,kind='native-ui')
    print(json.dumps(report,ensure_ascii=False));return 0
