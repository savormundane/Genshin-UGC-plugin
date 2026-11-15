"""Independent offline image metadata, rich-text pixel tiles and read-only GIL layouts."""
from pathlib import Path
import argparse, hashlib, json, sys, tempfile, os

def image_info(path):
    from PIL import Image
    path=Path(path)
    with Image.open(path) as im:
        return {'width':im.width,'height':im.height,'mode':im.mode,'format':im.format,
                'frames':getattr(im,'n_frames',1),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def layouts(path):
    from level_inventory import container
    path=Path(path)
    if path.suffix.lower()!='.gil':raise ValueError('layouts requires .gil')
    container(path.read_bytes())
    runtime=Path(__file__).resolve().parents[1]/'vendor/ayaya'
    sys.path[:0]=[str(runtime),str(runtime/'private_extensions')]
    from ugc_file_tools.gil_dump_codec.dump_json_tree import load_gil_payload_as_dump_json_object
    from ugc_file_tools.ui.readable_dump import extract_ui_record_list, extract_primary_guid, extract_primary_name
    dump=load_gil_payload_as_dump_json_object(path.resolve(),max_depth=16)
    payload=dump.get('4')
    if not isinstance(payload,dict):raise ValueError('Unknown GIL payload schema')
    records=extract_ui_record_list(dump) if payload.get('9') is not None else []
    from ugc_file_tools.ui_patchers.layout.layout_templates_parts.shared_parts.models import DEFAULT_LIBRARY_ROOT_GUID
    result=[]; seen=set()
    for record in records:
        if not isinstance(record,dict) or '504' in record:continue
        guid=extract_primary_guid(record)
        if not isinstance(guid,int):raise ValueError('Layout root without GUID')
        if guid==DEFAULT_LIBRARY_ROOT_GUID:continue
        if guid in seen:raise ValueError('Duplicate layout root GUID')
        seen.add(guid);result.append({'id':guid,'name':extract_primary_name(record)})
    return {'layouts':result,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'schema':'bundled Ayaya UI root records without parent field 504','read_only':True}

from asset_core import compile_tiles


def convert(source, output, **options):
    from PIL import Image
    source=Path(source).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Output directory exists; choose a new directory')
    original=hashlib.sha256(source.read_bytes()).hexdigest()
    with Image.open(source) as image:
        if getattr(image,'n_frames',1)!=1:raise ValueError('Extract animation frames explicitly before conversion')
        preview,tiles=compile_tiles(image,**options)
    value={'schema':1,'source_sha256':original,'grid_size':list(preview.size),'cell':options.get('cell',16),
           'fit':options.get('fit','auto'),'coordinate_space':'top_left_design_units',
           'tiles':tiles,'textboxes':len(tiles),'utf8_bytes':sum(len(t['text'].encode('utf-8')) for t in tiles),
           'preview_kind':'reference raster; not rendered game text','gil_written':False,'host_tested':False}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pixel-text-',dir=output.parent) as td:
        stage=Path(td)/'output';stage.mkdir()
        (stage/'tiles.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        preview.save(stage/'preview.png')
        def lua_string(text):return '"'+text.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"'
        rows=['{x=%s,y=%s,width=%s,height=%s,fontSize=%s,text=%s}'%(t['x'],t['y'],t['width'],t['height'],t['font_size'],lua_string(t['text'])) for t in tiles]
        (stage/'data.lua').write_text('return {tiles={'+',\n'.join(rows)+'}}\n',encoding='utf-8')
        cells=[]
        for t in tiles:
            # Browser artifact uses explicit cells, avoiding a claim of font-metric parity.
            x=t['x']//value['cell'];y=t['y']//value['cell']
            for dx in range(t['columns']):
                r,g,b,a=preview.getpixel((x+dx,y))
                cells.append(f'<i style="left:{(x+dx)*value["cell"]}px;top:{y*value["cell"]}px;background:rgb({r},{g},{b})"></i>')
        (stage/'preview.html').write_text('<!doctype html><meta charset="utf-8"><title>Pixel reference</title><style>i{position:absolute;width:%spx;height:%spx}</style>'%(value['cell'],value['cell'])+''.join(cells),encoding='utf-8')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=original:raise ValueError('Source changed during compilation')
        os.rename(stage,output)
    return {k:v for k,v in value.items() if k!='tiles'}

def main(argv=None):
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='op',required=True)
    for name in ('info','layouts'):
        c=s.add_parser(name);c.add_argument('source')
    c=s.add_parser('text');c.add_argument('source');c.add_argument('--out',required=True)
    for key,default in [('width',None),('height',None),('columns',64),('max-bytes',4096),('cell',16),('alpha-min',128)]:
        c.add_argument('--'+key,type=int,default=default,required=default is None)
    c.add_argument('--fit',choices=['auto','fixed'],default='auto')
    a=p.parse_args(argv)
    try:
        if a.op=='info':v=image_info(a.source)
        elif a.op=='layouts':v=layouts(a.source)
        else:v=convert(a.source,a.out,width=a.width,height=a.height,columns=a.columns,max_bytes=a.max_bytes,cell=a.cell,alpha_min=a.alpha_min,fit=a.fit)
        print(json.dumps(v,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,ImportError,TypeError,KeyError) as e:
        print(str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
