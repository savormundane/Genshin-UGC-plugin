"""Unified native static asset generation; no external fitter process is launched."""
from pathlib import Path
import argparse, hashlib, json, math, os, sys, tempfile
from authoring_io import sha_file, output_directory, write_json, finish

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

def prepare_source(source, *, target='auto', width=None, height=None, step=1, colors=96, alpha_min=128, max_controls=None, columns=64, max_bytes=4096, cell=16, fit='auto'):
    from asset_core import open_single_image
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
    raw = None
    if source.suffix.lower()=='.json':
        raw=source.read_bytes()
        original=hashlib.sha256(raw).hexdigest()
        image=procedural(json.loads(raw))
        size=grid_size(*image.size)
    else:
        original=sha_file(source)
        with open_single_image(source,MAX_SOURCE_PIXELS) as im:
            size=grid_size(*im.size)
            image=im.convert('RGBA')
    parameters = {'step':step,'colors':colors,'alpha_min':alpha_min,'columns':columns,
                  'max_bytes':max_bytes,'cell':cell,'fit':fit,'max_controls':max_controls}
    return image, size, original, raw, target, parameters


def compile_grid(image, size, target, parameters):
    from PIL import Image
    from asset_core import harden, compile_prepared
    resized = image.convert('RGBa').resize(size, Image.Resampling.BOX).convert('RGBA')
    return compile_prepared(harden(resized, parameters['alpha_min']), target, parameters['colors'],
                            parameters['columns'], parameters['max_bytes'], parameters['cell'], parameters['fit'])


def generate(source, output, *, from_preview=None, candidate=None, **options):
    from asset_core import harden
    output=Path(output).resolve()
    if output.exists():raise ValueError('Output exists; select a new directory')
    selection=None
    if (from_preview is None)!=(candidate is None):
        raise ValueError('--from-preview and --candidate must be used together')
    if from_preview is not None:
        if options:raise ValueError('Candidate parameters cannot be combined with generation overrides')
        from_preview=Path(from_preview).resolve()
        report_raw=from_preview.read_bytes()
        preview_report=json.loads(report_raw.decode('utf-8-sig'))
        if preview_report.get('schema')!=1 or preview_report.get('kind')!='asset-preview':
            raise ValueError('Expected an assets preview report')
        matches=[row for row in preview_report['candidates'] if row['name']==candidate]
        if len(matches)!=1:raise ValueError(f'Expected an exact preview candidate name: {candidate}')
        row=matches[0]
        if row['within_budget'] is False or row.get('within_quality') is False:
            raise ValueError(f'Preview candidate {candidate} exceeds a declared constraint')
        options=row['parameters']
        source=source or preview_report.get('source')
        selection={'candidate':candidate,'preview_sha256':hashlib.sha256(report_raw).hexdigest()}
    if source is None:raise ValueError('Provide SOURCE or use a preview report that records its source')
    source=Path(source).resolve()
    image, size, original, raw, target, parameters = prepare_source(source, **options)
    if selection is not None and original!=preview_report['source_sha256']:
        raise ValueError('Preview source digest differs; preview this input before generating')
    source_size = list(image.size)
    source_kind = 'shapes' if raw is not None else 'image'
    image = harden(image, parameters['alpha_min'])
    preview, data, count = compile_grid(image, size, target, parameters)
    max_controls = parameters['max_controls']
    if max_controls is not None and count>max_controls:
        adjust='use a smaller grid or fewer colors' if target=='rectangles' else 'use a smaller grid or review --columns and --max-bytes'
        raise ValueError(f'{count} controls exceed budget {max_controls} ({target}, {size[0]}x{size[1]} grid); {adjust}')
    if target=='rectangles':payload={'w':size[0],'h':size[1],'maxRects':count,**data};coordinate='top_left_grid_pixels'
    else:
        payload={'tiles':[{'x':t['x'],'y':t['y'],'width':t['width'],'height':t['height'],'fontSize':t['font_size'],'text':t['text']} for t in data['tiles']]};coordinate='top_left_design_units'
    report={'schema':1,'generator':'genshin-ugc-assets','source_kind':source_kind,'source_sha256':original,'source_size':source_size,'grid_size':list(size),'target':target,'controls':count,'coordinate_space':coordinate,
            'parameters':parameters,
            'preview_kind':'quantized reference raster; not host rendering','external_process_started':False,'gil_written':False,'host_tested':False}
    if selection is not None:
        report['preview_selection']=selection
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


def preview(source, output, *, display=None, min_grid=None, max_error=None, **options):
    from fractions import Fraction
    from PIL import Image, ImageChops, ImageStat
    from asset_core import harden

    source = Path(source).resolve()
    if Path(output).exists():
        raise ValueError('Output exists; select a new directory')
    if display is not None:
        if not isinstance(display,(list,tuple)) or len(display)!=2:
            raise ValueError('Display requires width and height')
        for value in display:
            positive(value, 'display dimension')
        if math.prod(display)>MAX_SOURCE_PIXELS:
            raise ValueError(f'Display exceeds {MAX_SOURCE_PIXELS} pixels')
    image, size, digest, _, target, parameters = prepare_source(source, **options)
    if min_grid is None:min_grid=(1,1)
    if not isinstance(min_grid,(list,tuple)) or len(min_grid)!=2:
        raise ValueError('Minimum grid requires width and height')
    for requested,available in zip(min_grid,size):
        positive(requested,'minimum grid dimension',available)
    if max_error is not None and (type(max_error) not in (int,float) or not 0<=max_error<=1):
        raise ValueError('Maximum error must be normalized RGBA MSE in [0,1]')
    min_scale=max(Fraction(requested,available) for requested,available in zip(min_grid,size))
    has_foreground=image.getchannel(3).getbbox() is not None
    display_size = tuple(display) if display is not None else size
    display_pixels = math.prod(display_size)
    source_display = image.convert('RGBa').resize(display_size, Image.Resampling.BOX)
    source_alpha = source_display.getchannel(3)
    source_mask = source_alpha.point([0]+[255]*255)
    source_size = list(image.size)
    image = harden(image, parameters['alpha_min'])
    limit = parameters['max_controls']
    colors = parameters['colors']
    candidates = [('original',size,colors)]
    alternatives = [('fewer-colors',size,max(1,colors//2))]
    for name,scale in (('grid-75',Fraction(3,4)),('smaller-grid',Fraction(1,2)),
                       ('grid-25',Fraction(1,4)),('grid-12.5',Fraction(1,8)),
                       ('grid-6.25',Fraction(1,16)),('minimum-grid',min_scale)):
        if scale<min_scale:
            continue
        grid=tuple(math.ceil(dimension*scale) for dimension in size)
        alternatives.extend([(name,grid,colors),(name+'-fewer-colors',grid,max(1,colors//2))])
    rows = []
    seen = set()
    with output_directory(output) as stage:
        source_display.convert('RGBA').save(stage/'source.png')
        for name, grid, palette_limit in candidates:
            if (grid,palette_limit) in seen:
                continue
            seen.add((grid,palette_limit))
            settings = {**parameters,'target':target,'width':grid[0],'height':grid[1],
                        'step':1,'colors':palette_limit}
            raster, _, controls = compile_grid(image, grid, target, settings)
            within_budget = None if limit is None else controls<=limit
            if name=='original' and within_budget is False:
                candidates.extend(alternatives)
            dest = stage/name
            dest.mkdir()
            raster.save(dest/'preview.png')
            displayed = raster.convert('RGBa').resize(display_size, Image.Resampling.BOX)
            if grid!=display_size:
                displayed.convert('RGBA').save(dest/'display.png')
            delta = ImageChops.difference(source_display, displayed)
            red, green, blue, alpha = delta.split()
            intensity = ImageChops.lighter(ImageChops.lighter(red,green),ImageChops.lighter(blue,alpha))
            intensity.save(dest/'difference.png')
            mask = displayed.getchannel(3).point([0]+[255]*255)
            gained = ImageChops.subtract(mask,source_mask).histogram()[255]
            lost = ImageChops.subtract(source_mask,mask).histogram()[255]
            error=sum(ImageStat.Stat(delta).sum2)/(display_pixels*4*255**2)
            rows.append({
                'name':name, 'parameters':settings, 'grid_size':list(grid), 'controls':controls,
                'within_budget':within_budget,'within_quality':None if max_error is None else error<=max_error,
                'error':error,
                'alpha':{'changed_pixels':display_pixels-alpha.histogram()[0],
                         'became_visible':gained,'became_transparent':lost},
                'preview':name+'/preview.png',
                'display_preview':name+('/display.png' if grid!=display_size else '/preview.png'),
                'difference':name+'/difference.png',
            })
        feasible = [row['name'] for row in rows if row['within_budget'] is True]
        budget_status = 'not_checked' if limit is None else 'passed' if feasible else 'failed'
        diagnostics = []
        if budget_status=='failed':
            diagnostics.append({'code':'asset_budget_unmet',
                                'message':'None of the tested settings meets the control budget. Try a different grid, palette, or text chunk size.',
                                'expected':limit,'actual':min(row['controls'] for row in rows)})
        quality_status='not_checked' if max_error is None else 'passed' if any(row['within_quality'] for row in rows) else 'failed'
        if quality_status=='failed':
            diagnostics.append({'code':'asset_quality_unmet','message':'None of the tested settings meets the error limit.',
                                'expected':max_error,'actual':min(row['error'] for row in rows)})
        viable=[row for row in rows if row['within_budget'] is not False and row['within_quality'] is not False
                and (row['controls'] or not has_foreground)]
        viable.sort(key=lambda row:(row['error'],row['alpha']['became_transparent']+row['alpha']['became_visible'],row['controls'],row['name']))
        if not viable:
            diagnostics.append({'code':'asset_search_no_candidate',
                                'message':'The tested grids and palettes produced no usable candidate that meets all declared limits.'})
        report = {
            'schema':1, 'kind':'asset-preview', 'status':'passed',
            'source':str(source), 'source_sha256':digest, 'source_size':source_size, 'display_size':list(display_size),
            'display_source':'source.png','target':target,
            'preview_kind':'quantized reference grid' if target=='text' else 'software rectangle reference',
            'error_metric':'normalized premultiplied RGBA MSE on the display grid',
            'checks':{'budget':{'status':budget_status,'limit':limit,'feasible_candidates':feasible},
                      'quality':{'status':quality_status,'max_error':max_error,
                                 'feasible_candidates':[row['name'] for row in rows if row['within_quality'] is True]},
                      'search':{'status':'passed' if viable else 'failed','min_grid':list(min_grid),'tested':len(rows)}},
            'diagnostics':diagnostics,'candidates':rows,'recommendations':[row['name'] for row in viable[:3]],'host':'not_checked',
        }
        write_json(stage/'report.json', report)
        finish(stage, {str(source):digest}, kind='asset-preview')
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
    p=argparse.ArgumentParser(prog='qianxing.py assets',description=__doc__)
    s=p.add_subparsers(dest='op',required=True)
    for name, description in (('generate','Write selected asset data'),('preview','Compare settings before generation')):
        c=s.add_parser(name,help=description)
        c.add_argument('source',nargs='?' if name=='generate' else None)
        c.add_argument('--out',required=True)
        c.add_argument('--target',choices=['auto','rectangles','text'],default=argparse.SUPPRESS)
        for key in ('width','height','step','colors','alpha-min','max-controls','columns','max-bytes','cell'):
            c.add_argument('--'+key,type=int,default=argparse.SUPPRESS)
        c.add_argument('--fit',choices=['auto','fixed'],default=argparse.SUPPRESS)
        if name=='preview':
            c.add_argument('--display',nargs=2,type=int,metavar=('WIDTH','HEIGHT'))
            c.add_argument('--min-grid',nargs=2,type=int,metavar=('WIDTH','HEIGHT'))
            c.add_argument('--max-error',type=float)
        else:
            c.add_argument('--from-preview',metavar='REPORT')
            c.add_argument('--candidate',metavar='NAME')
    for name, description in (('fit','Fit primitives to an image or layer manifest'),
                              ('check','Inspect asset statistics'),('diff','Compare asset statistics'),
                              ('import-gia','Read calibrated native rectangle assets'),
                              ('info','Inspect GIL UI import targets'),('text','Generate legacy text data'),
                              ('layouts','List supported rich-text layouts')):
        s.add_parser(name, help=description)
    a=p.parse_args(args)
    opts=vars(a).copy()
    operation=opts.pop('op')
    source=opts.pop('source')
    out=opts.pop('out')
    try:
        result = preview(source,out,**opts) if operation=='preview' else generate(source,out,**opts)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError,ImportError,TypeError,KeyError) as e:
        if operation=='preview':
            print(json.dumps({'status':'failed','checks':{},'diagnostics':[
                {'code':'asset_preview_failed','message':str(e),'source':str(source)}
            ]},ensure_ascii=False))
        else:
            print(str(e),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
