"""Read-only statistics and semantic comparisons for supported asset formats."""
from pathlib import Path
import argparse,json,math
from authoring_io import read_json,sha

def inspect(path):
    from PIL import Image
    path=Path(path);raw=path.read_bytes();image=None;controls=None;representation='image';extra={}
    checks={};diagnostics=[]
    if path.suffix.lower()=='.json':
        value=read_json(path)
        if isinstance(value,dict) and value.get('schema')==1 and 'shapes'in value:
            from asset_pipeline import procedural
            image=procedural(value);representation='shapes'
        elif isinstance(value,dict) and value.get('generator')=='genshin-ugc-assets' and value.get('schema')==1:
            representation=value['target'];data=value['data'];size=value['grid_size']
            if len(size)!=2 or any(type(n)is not int or n<=0 for n in size) or math.prod(size)>1048576:raise ValueError('Invalid asset dimensions')
            if representation=='rectangles':
                palette=data['palette'];rects=data['rects']
                if any(not isinstance(c,list) or len(c)!=4 or any(type(v)is not int or not 0<=v<=255 for v in c) for c in palette):raise ValueError('Invalid RGBA palette')
                image=Image.new('RGBA',tuple(size));used=set()
                for rect in rects:
                    if not isinstance(rect,list) or len(rect)!=5 or any(type(v)is not int for v in rect):raise ValueError('Invalid rectangle')
                    x,y,w,h,color=rect
                    if x<0 or y<0 or w<=0 or h<=0 or x+w>size[0] or y+h>size[1] or not 1<=color<=len(palette):raise ValueError('Rectangle outside grid or palette')
                    for yy in range(y,y+h):
                        for xx in range(x,x+w):
                            key=yy*size[0]+xx
                            if key in used:raise ValueError('Overlapping asset rectangles')
                            used.add(key);image.putpixel((xx,yy),tuple(palette[color-1]))
                controls=len(rects)
            elif representation=='text':
                tiles=data['tiles']
                for t in tiles:
                    if not isinstance(t.get('text'),str) or any(type(t.get(k))not in (int,float) or not math.isfinite(t[k]) for k in ('x','y','width','height','font_size')) or any(t[k]<=0 for k in ('width','height','font_size')):raise ValueError('Invalid text tile')
                controls=len(tiles);extra={'text_bytes':sum(len(t['text'].encode('utf-8')) for t in tiles),'tiles':tiles,'raster':'not_checked'}
            else:raise ValueError('Unknown asset representation')
            if value['controls']!=controls:raise ValueError('Declared control count differs from payload')
            parameters=value.get('parameters',{})
            for check,key,counts in [('control_budget','max_controls',[controls]),
                                     *([('text_tile_bytes','max_bytes',[len(t['text'].encode('utf-8')) for t in tiles])]
                                       if representation=='text' else [])]:
                limit=parameters.get(key)
                if limit is not None and (type(limit) is not int or limit<1):
                    raise ValueError(f'{key} must be a positive integer')
                actual=max(counts,default=0)
                status='not_checked' if limit is None else 'failed' if actual>limit else 'passed'
                checks[check]={'status':status,'limit':limit,'actual':actual}
                if status=='failed':
                    diagnostic={'code':'asset_'+check+'_exceeded','message':f'{key} limit exceeded',
                                'expected':limit,'actual':actual}
                    if check=='text_tile_bytes':
                        diagnostic['tiles']=[{'index':index,'bytes':size} for index,size in enumerate(counts) if size>limit]
                    diagnostics.append(diagnostic)
        else:raise ValueError('Unsupported asset JSON; expected shapes or generated asset schema 1')
    else:
        with Image.open(path)as original:
            if getattr(original,'n_frames',1)!=1:raise ValueError('Select a single animation frame')
            if original.width*original.height>1048576:raise ValueError('Image exceeds inspection pixel limit')
            image=original.convert('RGBA')
    if image is not None:
        pixels=list(image.getdata());extra={'size':list(image.size),'rgba_colors':len(set(pixels)),
             'transparent_pixels':sum(p[3]==0 for p in pixels),'partial_alpha_pixels':sum(0<p[3]<255 for p in pixels),
             'rgba_sha256':sha(image.tobytes())}
    return {'schema':1,'status':'failed' if diagnostics else 'passed','source_sha256':sha(raw),'source_bytes':len(raw),'representation':representation,'controls':controls,
            **extra,'checks':checks,'diagnostics':diagnostics,'scope':'input legality and representation statistics','platform_compatibility':'not_checked','host':'not_checked'}

def difference(left,right):
    a=inspect(left);b=inspect(right)
    keys=set(a)|set(b);ignore={'source_sha256','status','schema','scope','platform_compatibility','host'}
    return {'schema':1,'status':'failed' if any(row['status']=='failed' for row in (a,b)) else 'passed','before':a,'after':b,'changes':{k:{'before':a.get(k),'after':b.get(k)} for k in sorted(keys-ignore) if a.get(k)!=b.get(k)},'comparison':'representation statistics and exact normalized RGBA digest when available','host':'not_checked'}

def main(argv=None):
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='operation',required=True);s=sub.add_parser('check');s.add_argument('input');d=sub.add_parser('diff');d.add_argument('input');d.add_argument('other')
    a=p.parse_args(argv)
    try:
        r=inspect(a.input) if a.operation=='check' else difference(a.input,a.other)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        r={'schema':1,'status':'failed','checks':{},'diagnostics':[{'code':'asset_inspection_failed','message':str(exc)}]}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 2 if r['status']=='failed' else 0
