"""Explicit ordered Lua assembly with dependency checks and exact line mapping."""
from pathlib import Path
import argparse,json,re
from authoring_io import PLUGIN,sha,schema,read_json,resolve,output_directory,finish,write_json
MODULES={'runtime':'production_runtime.lua','ui':'runtime_ui.lua','algorithms':'runtime_algorithms.lua','multiplayer':'runtime_multiplayer.lua','sessions':'runtime_sessions.lua','storage':'runtime_storage.lua','migration':'runtime_migration.lua','assets':'runtime_assets.lua'}
def assemble(spec,base):
    schema(spec,('schema','sources','modules'),('sources',));parts=[];mapping=[];inputs={};seen=set();line=1
    def append(name,code,path,prefix='',suffix=''):
        nonlocal line
        chunks=('-- BEGIN '+name+'\n'+prefix+code.rstrip('\r\n')+'\n'+suffix)
        start=line+1+prefix.count('\n');end=start+len(code.rstrip('\r\n').splitlines())-1
        mapping.append({'file':name,'start':start,'end':end,'sha256':sha(Path(path).read_bytes())});parts.append(chunks);line+=chunks.count('\n')
    for item in spec.get('modules',[]):
        schema(item,('name','as'),('name','as'))
        name=item['name'];alias=item['as']
        if name not in MODULES or not re.fullmatch(r'[A-Za-z_]\w*',alias) or alias in seen:raise ValueError('Invalid module/alias')
        from level_authoring import LUA_KEYWORDS
        if alias in LUA_KEYWORDS:raise ValueError('Lua keyword alias')
        path=PLUGIN/'scripts'/MODULES[name];raw=path.read_bytes();inputs[str(path)]=sha(raw);seen.add(alias)
        append('@'+name,raw.decode('utf-8'),path,'local '+alias+' = (function()\n','end)()\n')
    for item in spec['sources']:
        schema(item,('id','source','requires'),('id','source'));ident=item['id']
        if ident in seen or not isinstance(ident,str) or not ident or any(x not in seen for x in item.get('requires',[])):raise ValueError('Duplicate/unordered dependency '+str(ident))
        path=resolve(base,item['source']);raw=path.read_bytes();inputs[str(path)]=sha(raw);seen.add(ident);append(item['source'],raw.decode('utf-8-sig'),path)
    if not parts:raise ValueError('No Lua input')
    code=''.join(parts)
    return code,{'schema':2,'segments':mapping,'inputs':inputs,'assembled_source_sha256':sha(code.encode('utf-8'))}
def locate(mapping,line):
    found=[s for s in mapping['segments'] if s['start']<=line<=s['end']]
    return None if not found else {'file':found[0]['file'],'line':line-found[0]['start']+1}
def build(path,out):
    p=Path(path).resolve();code,mapping=assemble(read_json(p),p.parent)
    with output_directory(out) as stage:
        (stage/'client.lua').write_text(code,encoding='utf-8',newline='\n');write_json(stage/'source-map.json',mapping)
        return finish(stage,{str(p):sha(p.read_bytes()),**mapping['inputs']},kind='client-assembly')
def main(argv=None):
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='op',required=True);a=s.add_parser('assemble');a.add_argument('spec');a.add_argument('--out',required=True)
    a=s.add_parser('locate');a.add_argument('mapping');a.add_argument('line',type=int);a.add_argument('--gil');a.add_argument('--script-mapping')
    a=s.add_parser('check');a.add_argument('input');a.add_argument('--mapping');a.add_argument('--source-map');a.add_argument('--contract');a.add_argument('--out');a=p.parse_args(argv)
    if a.op=='assemble':result=build(a.spec,a.out)
    elif a.op=='check':
        from miliastra.client.check import inspect
        result=inspect(a.input,mapping=a.mapping,source_map=read_json(a.source_map)if a.source_map else None,contract=read_json(a.contract)if a.contract else None)
        if a.out:
            with Path(a.out).open('x',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False);f.write('\n')
    else:
        mapping=read_json(a.mapping)
        if a.gil:
            from joint_simulator import script_from_gil
            code,_=script_from_gil(Path(a.gil).read_bytes(),a.script_mapping or mapping.get('embedded_mapping','main.lua'))
            if sha(code.encode('utf-8'))!=mapping.get('embedded_source_sha256',mapping.get('assembled_source_sha256')):raise ValueError('Source map differs from embedded Lua')
        result=locate(mapping,a.line)
    print(json.dumps(result,ensure_ascii=False));return 1 if a.op=='check'and result['status']in ('failed','not_checked')else 0
