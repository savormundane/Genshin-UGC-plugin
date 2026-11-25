"""Lossless calibrated XY rectangle GIA import, dependency and projection checks."""
from pathlib import Path
import argparse,json,math,struct
from authoring_io import finish, output_directory, read_json, schema, sha, write_json
from miliastra.native.core import get
from level_inventory import container,fields,vals

def primitive_group_gia(name, parts):
    """Pack native decoration transform and colour carriers into a closed GIA group."""
    from level_authoring import msg,integer,text,pack
    dependencies=[];links=[]
    for index,(model,transform,colour) in enumerate(parts,10):
        body=integer(2,model)+msg(5,integer(1,1)+msg(11,transform))+msg(5,integer(1,22)+msg(32,colour))
        dependencies.append(msg(2,msg(1,integer(4,index))+msg(21,msg(1,body))))
        links.append(msg(2,integer(4,index)))
    if not links:raise ValueError('An empty fitted raster has no GIA prefab; omit gia for empty assets')
    return pack(msg(1,text(3,name)+b''.join(links))+b''.join(dependencies),(1,806,3))


def export_rectangles(data,anchor=(0,0),name='FittedAsset'):
    """Serialize the same calibrated XY rectangle dialect accepted by extract."""
    from level_authoring import msg,integer,flt
    parts=[]
    for x,y,w,h,c in data['rects']:
        r,g,b,a=data['palette'][c-1]
        transform=msg(1,flt(1,x+w/2-anchor[0])+flt(2,anchor[1]-y-h/2))+msg(2,flt(1,-90))+msg(3,flt(1,w)+flt(3,h))
        parts.append((10009001,transform,integer(3,(a<<24)|(r<<16)|(g<<8)|b)))
    result=primitive_group_gia(name,parts)
    extract(result,{'schema':2,'projection':'xy_x90','unit':1,'max_controls':len(parts),'anchor':list(anchor)})
    return result

def floating(b,n,default=0):
    values=[v for a,w,v,r in fields(b)if a==n]
    if not values:return default
    if len(values)!=1:raise ValueError('Ambiguous transform')
    v=struct.unpack('<f',values[0])[0]
    if not math.isfinite(v):raise ValueError('Non-finite transform')
    return v
def raster(rects,unit,max_controls,bounds):
    minx,miny,maxx,maxy=bounds
    width,height=round((maxx-minx)/unit),round((maxy-miny)/unit)
    if width<1 or height<1 or width*height>1048576:raise ValueError('Imported grid capacity')
    grid=[None]*(width*height)
    for x,y,w,h,color,*_ in rects:
        original=[x+w/2,y+h/2,w,h]
        values=[(x-minx)/unit,(y-miny)/unit,w/unit,h/unit]
        if any(abs(v-round(v))>1e-4 for v in values):raise ValueError('Geometry not on declared grid')
        x,y,w,h=map(round,values)
        restored=[minx+(x+w/2)*unit,miny+(y+h/2)*unit,w*unit,h*unit]
        if any(struct.pack('<f',a)!=struct.pack('<f',b)for a,b in zip(original,restored)):raise ValueError('Grid conversion changes source float32 geometry')
        for row in range(y,y+h):
            for col in range(x,x+w):
                idx=(height-1-row)*width+col
                if not 0<=idx<len(grid):raise ValueError('Primitive extent mismatch')
                if grid[idx]is not None and (grid[idx]!=color or (color>>24)not in(0,255)):raise ValueError('Overlapping colors/transparency require distinct explicit depth layers')
                grid[idx]=color
    palette=[];indices={};merged=[];active={}
    for y in range(height):
        row={};x=0
        while x<width:
            color=grid[y*width+x]
            if color is None:x+=1;continue
            end=x+1
            while end<width and grid[y*width+end]==color:end+=1
            if color not in indices:
                indices[color]=len(palette)+1;palette.append([(color>>16)&255,(color>>8)&255,color&255,(color>>24)&255])
            key=(x,end-x,color);r=active.get(key)
            if r:r[3]+=1
            else:r=[x,y,end-x,1,indices[color]];merged.append(r)
            row[key]=r;x=end
        active=row
    if len(merged)>max_controls:raise ValueError('Imported asset exceeds control budget')
    return width,height,merged,palette

def extract(data,spec):
    schema(spec,('schema','projection','unit','max_controls','names','anchor','layers'),('projection','unit','max_controls'))
    if spec['projection']!='xy_x90' or type(spec['unit'])not in(int,float)or not math.isfinite(spec['unit'])or spec['unit']<=0:raise ValueError('Calibrated projection xy_x90 and positive grid unit required')
    if type(spec['max_controls'])!=int or spec['max_controls']<1:raise ValueError('Positive control budget required')
    layers=spec.get('layers')
    if layers is not None:
        if not isinstance(layers,list)or not layers or any(type(z)not in(int,float)or not math.isfinite(z)for z in layers)or len(set(layers))!=len(layers):raise ValueError('Explicit unique finite depth layers required')
    anchor=spec.get('anchor',[0,0])
    if not isinstance(anchor,list)or len(anchor)!=2 or any(type(v)not in(int,float)or not math.isfinite(v)for v in anchor):raise ValueError('Finite XY anchor required')
    header,root=container(data)
    if header[3]!=3:raise ValueError('Expected calibrated GIA container')
    prefabs=vals(root,1);related={};assets=[]
    for r in vals(root,2):
        ident=get(get(r,1,default=b''),4,0)
        if ident is None:ident=get(get(r,1,default=b''),4)
        if ident in related:raise ValueError('Duplicate dependency ID')
        related[ident]=r
    names=set(spec.get('names',[]));found=set()
    for prefab in prefabs:
        name=get(prefab,3,default=b'').decode('utf-8')
        if names and name not in names:continue
        if name in found:raise ValueError('Ambiguous prefab name')
        found.add(name);rects=[];dependencies=[];primitives=[];plane=None
        for link in vals(fields(prefab),2):
            ident=get(link,4,0)
            if ident is None:ident=get(link,4)
            if ident not in related:raise ValueError('Missing GIA dependency')
            dependencies.append(ident);asset=related[ident];body=get(asset,21)
            if not body:raise ValueError('Unsupported dependency geometry')
            d=get(body,1,default=b'');comps=vals(fields(d),5);trans=[c for c in comps if get(c,1,0)==1];colors=[c for c in comps if get(c,1,0)==22]
            if len(trans)!=1 or len(colors)!=1 or get(d,2,0)!=10009001:raise ValueError('Uncalibrated primitive')
            if any(get(c,1,0)not in(1,22)for c in comps):raise ValueError('Unsupported primitive component')
            tr=get(trans[0],11,default=b'');pos=get(tr,1,default=b'');rot=get(tr,2,default=b'');scale=get(tr,3,default=b'')
            if [floating(rot,i)for i in(1,2,3)]!=[-90,0,0]:raise ValueError('Unsupported rotation/projection')
            z=floating(pos,3)
            if layers is None and plane is not None and z!=plane:raise ValueError('Multiple depth layers require explicit layers')
            if layers is not None and z not in layers:raise ValueError('Primitive depth absent from explicit layers')
            plane=z
            if floating(scale,2,1)!=1:raise ValueError('Unsupported normal-axis scale')
            color=get(get(colors[0],32,default=b''),3,0)
            if color is None or not 0<=color<=0xffffffff:raise ValueError('No calibrated packed ARGB color')
            x,y=floating(pos,1),floating(pos,2);w,h=floating(scale,1,1),floating(scale,3,1)
            if w<=0 or h<=0:raise ValueError('Invalid primitive scale')
            primitives.append({'resource_id':str(ident),'template_id':10009001,'position':[x,y,z],'rotation':[-90,0,0],'scale':[w,1,h],'argb':color,'layer':z})
            rects.append([x-w/2,y-h/2,w,h,color,z])
        if not rects:raise ValueError('Empty prefab')
        unit=spec['unit'];minx=min(r[0]for r in rects);miny=min(r[1]for r in rects);maxx=max(r[0]+r[2]for r in rects);maxy=max(r[1]+r[3]for r in rects)
        merged=[];palette=[];layer_records=[]
        for depth in (layers if layers is not None else[plane]):
            selected=[r for r in rects if r[5]==depth]
            if not selected:continue
            width,height,rows,colors=raster(selected,unit,spec['max_controls'],(minx,miny,maxx,maxy))
            start=len(merged);offset=len(palette);palette.extend(colors)
            merged.extend([x,y,w,h,c+offset]for x,y,w,h,c in rows)
            layer_records.append({'depth':depth,'first_rect':start+1,'rect_count':len(rows)})
        if len(merged)>spec['max_controls']:raise ValueError('Imported asset exceeds total layered control budget')
        layered={'layers':layer_records,'layer_order':'explicit_back_to_front'}if layers is not None else{}
        plane=plane if layers is None else None
        assets.append({'name':name,'width':width,'height':height,'world_origin':[minx,miny],'plane_z':plane,'unit':unit,'anchor':anchor,'source_anchor':{'world':[0,0,plane],'grid':[-minx/unit,maxy/unit]},'dependencies':[str(i)for i in dependencies],'primitives':primitives,'data':{'rects':merged,'palette':palette,**layered},'source_primitives':len(rects)})
    if names-found:raise ValueError('Selected GIA names absent: '+str(names-found))
    if not assets:raise ValueError('No selected prefabs')
    return assets
def build(source,spec_path,out):
    p=Path(source).resolve();sp=Path(spec_path).resolve();raw=p.read_bytes();assets=extract(raw,read_json(sp))
    from miliastra.assets.pipeline import lua
    from PIL import Image,ImageDraw
    with output_directory(out)as stage:
        directory=[]
        for i,a in enumerate(assets):
            dest=stage/str(i);dest.mkdir();record={'schema':2,'target':'rectangles','source_sha256':sha(raw),'coordinate_space':'top_left_grid_pixels',**a}
            write_json(dest/'asset.json',record);(dest/'data.lua').write_text('return '+lua({'w':a['width'],'h':a['height'],'maxRects':len(a['data']['rects']),**a['data']})+'\n',encoding='utf-8')
            image=Image.new('RGBA',(a['width'],a['height']));draw=ImageDraw.Draw(image)
            for x,y,w,h,c in a['data']['rects']:
                color=tuple(a['data']['palette'][c-1])
                if 'layers'in a['data']:
                    overlay=Image.new('RGBA',image.size);ImageDraw.Draw(overlay).rectangle((x,y,x+w-1,y+h-1),fill=color)
                    image=Image.alpha_composite(image,overlay)
                else:draw.rectangle((x,y,x+w-1,y+h-1),fill=color)
            image.save(dest/'preview.png');directory.append({'name':a['name'],'path':str(i)+'/asset.json','anchor':a['anchor']})
        write_json(stage/'catalog.json',{'schema':2,'assets':directory})
        return finish(stage,{str(p):sha(raw),str(sp):sha(sp.read_bytes())},kind='native-assets',assets=len(assets),lossless=True,preview_kind='software reconstruction')
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--spec',required=True);p.add_argument('--out',required=True);a=p.parse_args(argv)
    print(json.dumps(build(a.source,a.spec,a.out),ensure_ascii=False));return 0
