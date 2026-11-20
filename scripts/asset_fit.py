"""Deterministic, budgeted premultiplied-RGBA fitting; no external executable."""
from pathlib import Path
import argparse, json, math, random
from PIL import Image, ImageDraw, ImageChops, ImageStat
from authoring_io import read_json, write_json, sha, canonical, output_directory, finish
from asset_pipeline import lua

MAX_FIT_PIXELS = 262_144


def parameters(spec):
    allowed = {'schema', 'shapes', 'budget', 'work', 'seed', 'alpha_min', 'target_error', 'regions', 'anchor','gia','max_controls'}
    version = spec.get('schema') if isinstance(spec,dict) else None
    if version == 2: allowed.add('max_total_controls')
    if not isinstance(spec, dict) or set(spec) - allowed or type(version)!=int or version not in (1,2):
        raise ValueError('Fit schema 1 or 2 required; uncalibrated transforms and unknown fields are refused')
    cfg = dict(shapes=['rect', 'ellipse', 'circle', 'line'], budget=100, work=2000,
               seed=0, alpha_min=1, target_error=0, regions=[], anchor=[0, 0],gia=False,max_controls=10000)
    cfg.update({k:v for k,v in spec.items() if k != 'schema'})
    if not isinstance(cfg['shapes'], list) or not cfg['shapes'] or len(set(cfg['shapes'])) != len(cfg['shapes']) or set(cfg['shapes']) - {'rect','ellipse','circle','line'}:
        raise ValueError('Select unique rect, ellipse, circle, line shapes')
    if type(cfg['gia'])!=bool:raise ValueError('gia must be boolean')
    for key, low, high in [('budget',1,10000),('work',1,1000000),('seed',0,2**32-1),('alpha_min',1,255),('max_controls',1,262144)]:
        if type(cfg[key]) != int or not low <= cfg[key] <= high:
            raise ValueError('Invalid bounded integer: '+key)
    if type(cfg['target_error']) not in (int,float) or not math.isfinite(cfg['target_error']) or not 0 <= cfg['target_error'] <= 1:
        raise ValueError('target_error must be normalized RGBA MSE in [0,1]')
    if not isinstance(cfg['regions'],list) or any(not isinstance(b,list) or len(b)!=4 or any(type(x)!=int for x in b) for b in cfg['regions']):
        raise ValueError('regions must contain integer [left,top,right,bottom] boxes, exclusive end')
    if not isinstance(cfg['anchor'],list) or len(cfg['anchor'])!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in cfg['anchor']):
        raise ValueError('anchor must contain two finite pixel coordinates')
    if version == 2:
        cfg['schema'] = 2
        total = cfg.get('max_total_controls')
        if 'max_total_controls' in cfg and (type(total)!=int or total<1): raise ValueError('Positive max_total_controls required')
    return cfg


def paint(size, shape):
    if not isinstance(shape,dict) or set(shape) != {'kind','box','color'} or shape['kind'] not in ('rect','ellipse','circle','line'):
        raise ValueError('Unknown primitive contract')
    b,c = shape['box'],shape['color']
    if not isinstance(b,list) or len(b)!=4 or any(type(x)!=int for x in b) or not (0<=b[0]<b[2]<=size[0] and 0<=b[1]<b[3]<=size[1]):
        raise ValueError('Primitive outside image bounds')
    if not isinstance(c,list) or len(c)!=4 or any(type(x)!=int or not 0<=x<=255 for x in c):
        raise ValueError('RGBA channels must be bytes')
    if shape['kind']=='circle' and b[2]-b[0]!=b[3]-b[1]:raise ValueError('Circle needs a square box')
    if shape['kind']=='line' and min(b[2]-b[0],b[3]-b[1])!=1:raise ValueError('Only axis-aligned one-pixel lines are calibrated here')
    layer=Image.new('RGBA',size);draw=ImageDraw.Draw(layer)
    bounds=(b[0],b[1],b[2]-1,b[3]-1)
    if shape['kind'] in ('rect','line'):draw.rectangle(bounds,fill=tuple(c))
    else:draw.ellipse(bounds,fill=tuple(c))
    return layer


def render(size, shapes):
    image=Image.new('RGBA',size)
    for shape in shapes:image=Image.alpha_composite(image,paint(size,shape))
    return image


def error(image, target):
    return sum(ImageStat.Stat(ImageChops.difference(image.convert('RGBa'),target.convert('RGBa'))).sum2)/(image.width*image.height*4*255**2)


def fit(image, cfg, binding, state=None, steps=None, initial=None):
    """Each work unit is one evaluated proposal. Resume preserves the exact RNG stream."""
    if cfg.get('schema') == 2:
        from asset_fit_v2 import fit as fit_v2
        return fit_v2(image,cfg,binding,state,steps,initial)
    size=image.size
    if size[0]*size[1]>MAX_FIT_PIXELS:
        raise ValueError(f'Fit input exceeds {MAX_FIT_PIXELS} pixels; preprocess explicitly')
    regions=cfg['regions'] or [[0,0,*size]]
    if any(not(0<=l<r<=size[0] and 0<=t<b<=size[1]) for l,t,r,b in regions):raise ValueError('Region outside image')
    region_mask=Image.new('L',size);draw=ImageDraw.Draw(region_mask)
    for l,t,r,b in regions:draw.rectangle((l,t,r-1,b-1),fill=255)
    silhouette=image.getchannel('A').point(lambda a:255 if a>=cfg['alpha_min'] else 0)
    allowed=ImageChops.multiply(silhouette,region_mask)
    points=[(i%size[0],i//size[0]) for i,a in enumerate(allowed.getdata()) if a]
    rng=random.Random(cfg['seed']);shapes=list(initial or []);done=0
    image_so_far=render(size,shapes);current=error(image_so_far,image);history=[current]
    if len(shapes)>cfg['budget']:raise ValueError('Initial primitives exceed budget')
    if state is not None:
        if state.get('schema')!=1 or state.get('binding')!=binding:raise ValueError('Resume input/configuration digest mismatch')
        checksum=state.get('sha256');body={k:v for k,v in state.items() if k!='sha256'}
        if checksum!=sha(canonical(body).encode()):raise ValueError('Resume state checksum mismatch')
        shapes=state['shapes'];image_so_far=render(size,shapes);done=state['work_done']
        if type(done)!=int or not 0<=done<=cfg['work'] or len(shapes)>cfg['budget']:raise ValueError('Invalid resume work/budget')
        current=error(image_so_far,image);history=state['errors']
        if not history or current!=history[-1] or any(b>=a for a,b in zip(history,history[1:])):raise ValueError('Invalid resume error history')
        rng.setstate((state['rng'][0],tuple(state['rng'][1]),state['rng'][2]))
    limit=cfg['work'] if steps is None else min(cfg['work'],done+steps)
    if steps is not None and (type(steps)!=int or steps<=0):raise ValueError('steps must be positive')
    while done<limit and current>cfg['target_error'] and points:
        # Global proposals alternate with local refinements of the last accepted primitive.
        local=bool(shapes) and (done%3==2 or len(shapes)>=cfg['budget'])
        x,y=rng.choice(points);kind=rng.choice(cfg['shapes'])
        scale=max(1,round(max(size)*(1-done/cfg['work'])/2))
        w=rng.randint(1,min(scale,size[0]));h=rng.randint(1,min(scale,size[1]))
        if kind=='circle':w=h=min(w,h)
        if kind=='line':
            if rng.randrange(2):w=1
            else:h=1
        left=max(0,min(size[0]-w,x-w//2));top=max(0,min(size[1]-h,y-h//2))
        box=[left,top,min(size[0],left+w),min(size[1],top+h)]
        color=list(image.getpixel((x,y)));prefix=shapes
        if local:
            old=shapes[-1];kind=old['kind'];box=old['box'][:];color=old['color'][:];prefix=shapes[:-1]
            move=rng.choice((-1,1));axis=rng.randrange(2)
            if 0<=box[axis]+move and box[axis+2]+move<=size[axis]:box[axis]+=move;box[axis+2]+=move
            color=list(image.getpixel(((box[0]+box[2]-1)//2,(box[1]+box[3]-1)//2)))
        proposal={'kind':kind,'box':box,'color':color};done+=1
        if local:
            old_coverage=paint(size,shapes[-1]).getchannel('A').point(lambda a:255 if a else 0)
            if ImageChops.subtract(old_coverage,region_mask).getbbox():continue
        layer=paint(size,proposal)
        coverage=layer.getchannel('A').point(lambda a:255 if a else 0)
        if ImageChops.subtract(coverage,allowed).getbbox():continue
        base=render(size,prefix) if local else image_so_far
        candidate=Image.alpha_composite(base,layer);score=error(candidate,image)
        if score<current:
            shapes=prefix+[proposal];image_so_far=candidate;current=score;history.append(score)
    result={'schema':1,'binding':binding,'shapes':shapes,'work_done':done,'errors':history,'rng':rng.getstate()}
    result['sha256']=sha(canonical(result).encode())
    return result,image_so_far


def rectangle_data(image):
    """Losslessly lower the reconstructed raster to the existing rectangle/Lua contract."""
    palette=[];ids={};rects=[];previous={};pixels=image.load()
    for y in range(image.height):
        active={};x=0
        while x<image.width:
            color=pixels[x,y]
            if not color[3]:x+=1;continue
            end=x+1
            while end<image.width and pixels[end,y]==color:end+=1
            if color not in ids:ids[color]=len(palette)+1;palette.append(list(color))
            key=(x,end-x,ids[color])
            if key in previous:row=previous[key];row[3]+=1
            else:row=[x,y,end-x,1,ids[color]];rects.append(row)
            active[key]=row;x=end
        previous=active
    return {'rects':rects,'palette':palette}


def build(source,spec_path,out,resume=None,steps=None,initial=None):
    if resume and initial:raise ValueError('Choose resume or initial, not both')
    source=Path(source).resolve();sp=Path(spec_path).resolve();cfg=parameters(read_json(sp))
    inputs={str(source):sha(source.read_bytes()),str(sp):sha(sp.read_bytes())}
    # A JSON source is an explicit layer manifest. Paths are relative to it, never discovered.
    if source.suffix.lower()=='.json':
        batch=read_json(source)
        if set(batch)!={'schema','layers'} or batch['schema']!=1 or not isinstance(batch['layers'],list) or not batch['layers']:raise ValueError('Expected schema 1 layers manifest')
        layers=batch['layers']
    else:layers=[{'name':'image','source':source.name}]
    names=set();items=[]
    for layer in layers:
        if set(layer)!={'name','source'} or not isinstance(layer['name'],str) or not layer['name'].isascii() or not layer['name'].replace('-','').replace('_','').isalnum() or layer['name'] in names:raise ValueError('Unique simple layer names required')
        names.add(layer['name']);path=(source.parent/layer['source']).resolve()
        if not path.is_relative_to(source.parent):raise ValueError('Layer dependency outside source directory')
        inputs[str(path)]=sha(path.read_bytes())
        with Image.open(path) as im:
            width, height = im.size
            if width * height > MAX_FIT_PIXELS:
                raise ValueError(f'{path.name}: {width}x{height} exceeds {MAX_FIT_PIXELS} pixels; preprocess explicitly')
            if getattr(im,'n_frames',1)!=1:raise ValueError('Use explicit layers for animated input')
            image=im.convert('RGBA')
        items.append((layer['name'],image,inputs[str(path)]))
    previous=read_json(resume) if resume else {};seed_data=read_json(initial) if initial else {}
    for extra in (resume,initial):
        if extra:inputs[str(Path(extra).resolve())]=sha(Path(extra).read_bytes())
    initial_data=previous.get('initial_data',{}) if resume else seed_data
    version=cfg.get('schema',1)
    count=len(items);total=cfg.get('max_total_controls',count*cfg['max_controls'])
    if version==2 and total<count: raise ValueError('Total controls smaller than layer count')
    quotas=[min(cfg['max_controls'],total//count+(i<total%count)) for i in range(count)] if version==2 else [cfg['max_controls']]*count
    binding=sha(canonical({'source':inputs[str(source)],'layers':[(n,d) for n,_,d in items],'config':cfg,'initial':initial_data}).encode())
    if resume and (previous.get('schema')!=version or previous.get('binding')!=binding or set(previous.get('layers',{}))!=names):raise ValueError('Resume input/configuration digest mismatch or missing layer state')
    if initial and (seed_data.get('schema') not in (1,2) or set(seed_data.get('layers',{}))!=names):raise ValueError('Initial state needs matching layer names')
    with output_directory(out) as stage:
        states={};catalog=[]
        for i,(name,image,digest) in enumerate(items):
            layer_cfg={**cfg,'max_controls':quotas[i]} if version==2 else cfg
            state,preview=fit(image,layer_cfg,binding,previous.get('layers',{}).get(name),steps,seed_data.get('layers',{}).get(name,{}).get('shapes'))
            states[name]=state;dest=stage/name;dest.mkdir();data=rectangle_data(preview)
            if len(data['rects'])>quotas[i]:raise ValueError('Lowered rectangle controls exceed max_controls; no output committed')
            record={'schema':1,'size':list(image.size),'coordinate_space':'top_left_pixels','anchor':cfg['anchor'],'source_sha256':digest,'config':cfg,'binding':binding,'primitives':state['shapes'],
                    'primitive_count':len(state['shapes']),'rectangle_controls':len(data['rects']),'error':state['errors'][-1],'error_history':state['errors'],'work_done':state['work_done'],
                    'preview':'software reconstruction','editor':'not_checked','host':'not_checked'}
            write_json(dest/'primitives.json',record);preview.save(dest/'preview.png')
            write_json(dest/'asset.json',{'schema':1,'generator':'genshin-ugc-assets','target':'rectangles','grid_size':list(image.size),'controls':len(data['rects']),'data':data})
            if cfg['gia']:
                from native_assets import export_rectangles
                (dest/'asset.gia').write_bytes(export_rectangles(data,cfg['anchor'],name))
            (dest/'data.lua').write_text('return '+lua({'w':image.width,'h':image.height,'maxRects':len(data['rects']),**data})+'\n',encoding='utf-8')
            catalog.append({'name':name,'path':name+'/asset.json','primitives':record['primitive_count'],'controls':record['rectangle_controls'],'error':record['error']})
            if version==2:
                metrics=dict(control_budget=quotas[i],palette_size=len(data['palette']),lua_utf8_bytes=(dest/'data.lua').stat().st_size,stats=state['stats'],stop_reason=state['stop_reason'],target_reached=state['target_reached'])
                record.update(schema=2,cost_history=state['history'],**metrics)
                write_json(dest/'primitives.json',record);catalog[-1].update(metrics)
        if version==2 and sum(r['controls'] for r in catalog)>total: raise ValueError('Total control budget exceeded')
        checkpoint={'schema':version,'binding':binding,'layers':states}
        if initial_data: checkpoint['initial_data']=initial_data
        write_json(stage/'state.json',checkpoint)
        summary={'schema':version,'layers':catalog,'binding':binding}
        if version==2: summary.update(max_total_controls=total,total_controls=sum(r['controls'] for r in catalog),total_lua_utf8_bytes=sum(r['lua_utf8_bytes'] for r in catalog),budget_kind='tool delivery budget; not platform limit')
        write_json(stage/'catalog.json',summary)
        return finish(stage,inputs,kind='asset-fit',binding=binding,layers=catalog,editor='not_checked',host='not_checked')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--spec',required=True);p.add_argument('--out',required=True)
    p.add_argument('--resume');p.add_argument('--initial');p.add_argument('--steps',type=int);a=p.parse_args(argv)
    print(json.dumps(build(a.source,a.spec,a.out,a.resume,a.steps,a.initial),ensure_ascii=False));return 0


if __name__=='__main__':raise SystemExit(main())
