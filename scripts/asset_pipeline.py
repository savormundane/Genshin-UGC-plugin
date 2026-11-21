"""Unified native static asset generation; no external fitter process is launched."""
from pathlib import Path
import argparse, hashlib, json, math, os, sys, tempfile
from authoring_io import sha_file

MAX_SOURCE_PIXELS = 16_777_216
MAX_GRID_PIXELS = 1_048_576

def positive(value,name,maximum=None):
    if type(value)!=int or value<1 or (maximum is not None and value>maximum):
        raise ValueError(name+' must be a positive integer'+(' <= '+str(maximum) if maximum else ''))

def procedural(spec):
    from PIL import Image, ImageDraw
    if not isinstance(spec,dict) or set(spec)!={'schema','size','shapes'} or type(spec['schema'])!=int or spec['schema']!=1:
        raise ValueError('Shape source requires schema=1, size and shapes only')
    size=spec['size']
    if not isinstance(size,list) or len(size)!=2:raise ValueError('size must be [width,height]')
    for v in size:positive(v,'canvas size',4096)
    if size[0]*size[1]>1048576:raise ValueError('Canvas exceeds 1048576 pixels')
    if not isinstance(spec['shapes'],list) or len(spec['shapes'])>10000:raise ValueError('shapes must contain at most 10000 items')
    canvas=Image.new('RGBA',tuple(size))
    for shape in spec['shapes']:
        if not isinstance(shape,dict):raise ValueError('Each shape must be an object')
        kind=shape.get('kind');required={'kind','box','color'} if kind in ('rect','ellipse') else {'kind','points','color','width'} if kind=='line' else None
        if required is None or set(shape)!=required:raise ValueError('Unknown shape kind or fields')
        color=shape['color']
        if not isinstance(color,list) or len(color)!=4 or any(type(c)!=int or not 0<=c<=255 for c in color):raise ValueError('color must be four integer RGBA channels')
        coordinates=shape['points'] if kind=='line' else shape['box']
        if not isinstance(coordinates,list) or len(coordinates)!=4 or any(type(v)!=int for v in coordinates):raise ValueError('Geometry requires four integer coordinates')
        x0,y0,x1,y1=coordinates
        if not (0<=x0<size[0] and 0<=x1<size[0] and 0<=y0<size[1] and 0<=y1<size[1]):raise ValueError('Geometry outside canvas')
        if kind!='line' and (x1<x0 or y1<y0):raise ValueError('Invalid shape box')
        layer=Image.new('RGBA',tuple(size));draw=ImageDraw.Draw(layer)
        if kind=='rect':draw.rectangle(coordinates,fill=tuple(color))
        elif kind=='ellipse':draw.ellipse(coordinates,fill=tuple(color))
        else:
            positive(shape['width'],'line width',4096)
            draw.line(coordinates,fill=tuple(color),width=shape['width'])
        canvas=Image.alpha_composite(canvas,layer)
    return canvas

def lua(value):
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        if not math.isfinite(value):raise ValueError('Nonfinite Lua value')
        return str(value)
    if isinstance(value,str):return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\r','\\r')+'"'
    if isinstance(value,list):return '{'+','.join(lua(v) for v in value)+'}'
    if isinstance(value,dict):return '{'+','.join('['+lua(k)+']='+lua(v) for k,v in value.items())+'}'
    raise ValueError('Unsupported Lua value')

def generate(source, output, *, target='auto', width=None, height=None, step=1, colors=96, alpha_min=128, max_controls=None, columns=64, max_bytes=4096, cell=16, fit='auto'):
    from PIL import Image
    from asset_core import harden, compile_prepared, open_single_image
    source=Path(source).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Output exists; select a new directory')
    if target not in ('auto','rectangles','text'):raise ValueError('Unknown target')
    target='rectangles' if target=='auto' else target
    for name,value,cap in [('step',step,None),('colors',colors,256),('alpha_min',alpha_min,255),('columns',columns,None),('max_bytes',max_bytes,None),('cell',cell,None)]:positive(value,name,cap)
    if max_controls is not None:positive(max_controls,'max_controls')
    if fit not in ('auto','fixed'):raise ValueError('Unknown fit')
    if (width is None)!=(height is None):raise ValueError('width and height must be supplied together')
    if width is not None:
        if step!=1:raise ValueError('Explicit dimensions cannot be combined with step')
        positive(width,'width');positive(height,'height')
    def grid_size(w,h):
        size=(width,height) if width is not None else ((w+step-1)//step,(h+step-1)//step)
        if size[0]*size[1]>MAX_GRID_PIXELS:
            raise ValueError(f'Grid {size[0]}x{size[1]} exceeds {MAX_GRID_PIXELS} pixels; increase --step or reduce --width and --height')
        return size
    if width is not None:grid_size(width,height)
    if source.suffix.lower()=='.json':
        raw=source.read_bytes()
        original=hashlib.sha256(raw).hexdigest()
        image=procedural(json.loads(raw))
        source_kind='shapes'
    else:
        original=sha_file(source)
        with open_single_image(source,MAX_SOURCE_PIXELS) as im:
            size=grid_size(*im.size)
            image=im.convert('RGBA')
        source_kind='image'
    source_size=list(image.size)
    if source_kind=='shapes':size=grid_size(*source_size)
    image=harden(image,alpha_min).convert('RGBa').resize(size,Image.Resampling.BOX).convert('RGBA')
    image=harden(image,alpha_min)
    preview,data,count=compile_prepared(image,target,colors,columns,max_bytes,cell,fit)
    if max_controls is not None and count>max_controls:
        adjust='use a smaller grid or fewer colors' if target=='rectangles' else 'use a smaller grid or review --columns and --max-bytes'
        raise ValueError(f'{count} controls exceed budget {max_controls} ({target}, {size[0]}x{size[1]} grid); {adjust}')
    if target=='rectangles':payload={'w':size[0],'h':size[1],'maxRects':count,**data};coordinate='top_left_grid_pixels'
    else:
        payload={'tiles':[{'x':t['x'],'y':t['y'],'width':t['width'],'height':t['height'],'fontSize':t['font_size'],'text':t['text']} for t in data['tiles']]};coordinate='top_left_design_units'
    report={'schema':1,'generator':'genshin-ugc-assets','source_kind':source_kind,'source_sha256':original,'source_size':source_size,'grid_size':list(size),'target':target,'controls':count,'coordinate_space':coordinate,
            'parameters':{'step':step,'colors':colors,'alpha_min':alpha_min,'columns':columns,'max_bytes':max_bytes,'cell':cell,'fit':fit,'max_controls':max_controls},
            'preview_kind':'quantized reference raster; not host rendering','external_process_started':False,'gil_written':False,'host_tested':False}
    asset={**report,'data':data}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ugc-assets-',dir=output.parent) as td:
        stage=Path(td)/'result';stage.mkdir()
        for filename,value in [('asset.json',asset),('report.json',report)]:
            (stage/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (stage/'data.lua').write_text('return '+lua(payload)+'\n',encoding='utf-8')
        preview.save(stage/'preview.png')
        if source_kind=='shapes':
            (stage/'source.json').write_bytes(raw)
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir()}
        (stage/'manifest.json').write_text(json.dumps({'schema':1,'files_sha256':files,'source_sha256':original,'target':target},indent=2)+'\n',encoding='utf-8')
        if sha_file(source)!=original:raise ValueError('Source changed during generation')
        os.rename(stage,output)
    return report

def main(argv=None):
    # Keep established info/text/layouts commands available through the same public entry.
    args=list(sys.argv[1:] if argv is None else argv)
    if args and args[0]=='fit':
        from asset_fit import main as fit_main
        return fit_main(args[1:])
    if args and args[0] in ('check','diff'):
        from asset_inspection import main as inspect_main
        return inspect_main(args)
    if args and args[0]=='import-gia':
        from native_assets import main as native_main
        return native_main(args[1:])
    if args and args[0] in ('info','text','layouts'):
        from assets_text import main as legacy
        return legacy(args)
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='op',required=True)
    c=s.add_parser('generate');c.add_argument('source');c.add_argument('--out',required=True);c.add_argument('--target',choices=['auto','rectangles','text'],default='auto')
    for key,default in [('width',None),('height',None),('step',1),('colors',96),('alpha-min',128),('max-controls',None),('columns',64),('max-bytes',4096),('cell',16)]:c.add_argument('--'+key,type=int,default=default)
    c.add_argument('--fit',choices=['auto','fixed'],default='auto');a=p.parse_args(args)
    try:
        opts=vars(a).copy();opts.pop('op');source=opts.pop('source');out=opts.pop('out')
        print(json.dumps(generate(source,out,**opts),ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,ImportError,TypeError,KeyError) as e:
        print(str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
