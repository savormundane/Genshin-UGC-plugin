"""Read an explicit GIL UI subtree into the pinned simulator's GIA reader.

This intermediate envelope is internal, not an editor-importable deliverable.
Original control bytes and child order are retained; no native fields are written.
"""
import base64
from authoring_io import schema,sha
from level_inventory import container,fields,vals,unique
from level_authoring import msg,integer,pack,stream,inspect_bindings,text
from native_core import get

def convert(data,config):
    schema(config,('source','sha256','root_guid','canvas'),('source','sha256','root_guid','canvas'))
    if sha(data)!=config['sha256']:raise ValueError('GIL digest mismatch')
    header,root=container(data)
    if header[3]!=2:raise ValueError('GIL required')
    if config['canvas'] not in ('pc-16-9','mobile-16-9'):raise ValueError('Unsupported canvas preset')
    if type(config['root_guid']) is not int:raise ValueError('Explicit root GUID required')
    binding=inspect_bindings(data)
    if binding['diagnostics']:raise ValueError('Invalid GIL bindings')
    records={}
    for raw in vals(fields(unique(root,9)),502):
        guid=get(raw,501,0)
        if guid in records:raise ValueError('Duplicate UI GUID')
        records[guid]=raw
    selected=[];seen=set()
    allowed={(1,12),(2,15),(4,86),(63,83),(64,84),(65,85),(67,90),(68,91),(70,93)}
    def visit(guid,parent=None):
        if guid in seen or guid not in records:raise ValueError('Missing or cyclic UI child')
        seen.add(guid);raw=records[guid]
        if parent is not None and get(raw,504,0)!=parent:raise ValueError('UI parent/child mismatch')
        components=vals(fields(raw),505);signatures=[(get(c,501,0),get(c,502,0)) for c in components]
        if len(signatures)!=len(set(signatures)) or set(signatures)-allowed:raise ValueError('Uncalibrated UI component; leave pending')
        if sum(s in signatures for s in ((64,84),(65,85),(68,91),(70,93)))!=1:raise ValueError('Unsupported or ambiguous UI kind')
        rect=next((c for c in components if get(c,501,0)==1),None)
        if rect is None:raise ValueError('Missing rectangle')
        overrides=vals(fields(rect),503)
        if len(overrides)!=1:raise ValueError('Ambiguous rectangle')
        states=vals(fields(get(get(overrides[0],13),12)),501)
        if sorted(get(s,501,0,0) for s in states)!=[0,1,2,3]:raise ValueError('Four explicit UI states required')
        for state in states:
            if get(get(state,502),508,default=b''):raise ValueError('Rotation calibration pending')
        # The chosen root is a local scope. Remove its external parent only in
        # the temporary envelope; preserve every other wire byte.
        scoped=b''.join(r for n,w,v,r in fields(raw) if not(parent is None and n==504))
        selected.append((guid,scoped))
        children=[]
        for n,w,v,r in fields(raw):
            if n==503:children.extend(stream(v) if w==2 else [v])
        if len(children)!=len(set(children)):raise ValueError('Duplicate UI child')
        actual={g for g,r in records.items() if get(r,504,0)==guid}
        if actual!=set(children):raise ValueError('Incomplete UI child list')
        for child in children:visit(child,guid)
    visit(config['root_guid'])
    envelope=b''
    for index,(guid,raw) in enumerate(selected):
        names=[get(get(c,12),501).decode('utf-8') for c in vals(fields(raw),505) if get(c,501,0)==2]
        if len(names)!=1:raise ValueError('Unique control name required')
        unit=msg(1,integer(2,1)+integer(3,8)+integer(4,guid))+text(3,names[0])+integer(5,70 if index==0 else 15)+msg(19,msg(1,raw))
        envelope+=msg(1 if index==0 else 2,unit)
    mounted=[b for b in binding['script_bindings'] if b['control_guid'] in seen]
    return {'envelope':base64.b64encode(pack(envelope,(1,806,3))).decode(),
            'canvas':config['canvas'],'root_guid':config['root_guid'],'guids':[g for g,_ in selected],
            'bindings':mounted,'scripts':binding['scripts'],
            'scope':'explicit_subtree','excluded_controls':len(records)-len(selected)}
