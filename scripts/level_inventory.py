"""Read-only GIL/GIA structure inventory. Never writes to the input."""
from pathlib import Path
import argparse,collections,hashlib,json,struct

def fields(data):
    pos=0;result=[]
    def varint():
        nonlocal pos
        value=0
        for shift in range(0,70,7):
            if pos>=len(data):raise ValueError('Truncated varint')
            c=data[pos];pos+=1
            if shift==63 and c>1:raise ValueError('Varint exceeds uint64')
            value|=(c&127)<<shift
            if c<128:return value
        raise ValueError('Invalid varint')
    while pos<len(data):
        start=pos;tag=varint();n,w=tag>>3,tag&7
        if not n or n>536870911:raise ValueError('Invalid field')
        if w==0:value=varint()
        elif w in (1,2,5):
            length=varint() if w==2 else 8 if w==1 else 4
            if pos+length>len(data):raise ValueError('Truncated field')
            value=data[pos:pos+length];pos+=length
        else:raise ValueError('Unsupported wire type')
        result.append((n,w,value,data[start:pos]))
    return result

def vals(fs,n,w=2):return [v for a,b,v,_ in fs if a==n and b==w]
def unique(fs,n,w=2,default=None):
    v=vals(fs,n,w)
    if len(v)>1:raise ValueError('Ambiguous field '+str(n))
    return v[0] if v else default

def container(data):
    if len(data)<24:raise ValueError('Container too short')
    h=struct.unpack('>5I',data[:20])
    if h[0]!=len(data)-4 or h[4]!=len(data)-24 or data[-4:]!=b'\0\0\x06\x79':raise ValueError('Unsupported framing')
    return h,fields(data[20:-4])

def graph_summary(blob):
    fs=fields(blob);ident=fields(unique(fs,1,default=b''));gid=unique(ident,5,0)
    nodes=vals(fs,3);readers=collections.Counter();indices=[];connections=[];pin_types=[];pin_values=[];literal_values=[]
    for raw in nodes:
        node=fields(raw);idx=unique(node,1,0);indices.append(idx)
        # Record node property layouts without guessing platform execution semantics.
        for key in [2,3]:
            prop=unique(node,key)
            if prop:
                nid=unique(fields(prop),5,0)
                if nid is not None:readers[str(nid)]+=1
    for raw in nodes:
        node=fields(raw);idx=unique(node,1,0)
        for pin in vals(node,4):
            pf=fields(pin);key=fields(unique(pf,1,default=b''))
            kind=unique(key,1,0,0);index=unique(key,2,0,0)
            pin_types.append([idx,kind,index,unique(pf,4,0)])
            value=unique(pf,3)
            if kind==3 and value is not None:pin_values.append([idx,kind,index,hashlib.sha256(value).hexdigest()])
            if kind==3 and value is not None and not vals(pf,5):literal_values.append([idx,kind,index,hashlib.sha256(value).hexdigest()])
            for connection in vals(pf,5):
                cf=fields(connection);remote=unique(cf,1,0)
                target=fields(unique(cf,2,default=b''))
                connections.append([idx,kind,index,remote,unique(target,1,0,0),unique(target,2,0,0)])
    name=unique(fs,2,default=b'').decode('utf-8',errors='replace')
    return {'id':gid,'name':name,'stored_nodes':len(nodes),'variables':sum(bool(raw) for raw in vals(fs,6)),
            'node_type_ids':dict(readers),'node_indices_unique':len(indices)==len(set(indices)),
            'variable_details':[{'name':unique(fields(raw),2,default=b'').decode('utf-8',errors='replace'),'type':unique(fields(raw),3,0),'bytes':len(raw)} for raw in vals(fs,6)],
            'pin_values':sorted(pin_values,key=repr),'literal_values':sorted(literal_values,key=repr),'connections':sorted(connections,key=repr),'pin_types':sorted(pin_types,key=repr),
            'dangling_node_refs':sorted({c[3] for c in connections if c[3] not in set(indices)},key=repr),
            'sha256':hashlib.sha256(blob).hexdigest()}

def graph_records(data):
    """Read ordinary and composite bodies without treating dependencies as roots."""
    header,root=container(data);records=[]
    if header[3]==3:
        for unit in vals(root,1)+vals(root,2):
            uf=fields(unit);wrapper=unique(uf,13)
            if wrapper is None:continue
            inner=unique(fields(wrapper),1,default=b'');raw=unique(fields(inner),1)
            if raw is None:raise ValueError('Unsupported GIA graph wrapper')
            identity=fields(unique(fields(raw),1,default=b''))
            kind=unique(identity,3,0)
            if kind not in(21001,21002):raise ValueError('Unsupported GIA graph kind '+str(kind))
            resource=fields(unique(uf,1,default=b''))
            if unique(resource,4,0)!=unique(identity,5,0):raise ValueError('GIA graph resource identity mismatch')
            records.append(('composite'if kind==21002 else'ordinary',raw))
    else:
        for section in vals(root,10):
            for key,kind in((1,'ordinary'),(4,'composite')):
                for wrapper in vals(fields(section),key):
                    raw=unique(fields(wrapper),1)
                    if raw is None:raise ValueError('Unsupported native graph wrapper')
                    records.append((kind,raw))
    return records


def graph_component_field(entity, section):
    if section == 4 and any(unique(fields(c), 1, 0) == 3 for c in vals(fields(entity), 7)):
        return 7
    return 6


def entity_graph_ids(entity, section=5):
    """Read graph bindings from an entity's calibrated component slots."""
    for component in vals(fields(entity), graph_component_field(entity, section)):
        cf = fields(component)
        if unique(cf, 1, 0) != 3:
            continue
        for group in vals(cf, 13):
            for entry in vals(fields(group), 1):
                locator = unique(fields(entry), 1, default=b'')
                yield unique(fields(locator), 2, 0)


def graph_library_ids(root):
    """Read category 4 graph registrations from editor folders and uncategorized tabs."""
    for library in vals(root, 6):
        for entry in vals(fields(library), 1):
            rows = fields(entry)
            if unique(rows, 1, 0) != 4:
                continue
            folders = collections.deque(vals(rows, 2) + vals(rows, 3))
            while folders:
                folder = fields(folders.popleft())
                folders.extend(vals(folder, 4))
                for raw in vals(folder, 5):
                    reference = fields(raw)
                    if unique(reference, 1, 0) == 800:
                        yield unique(reference, 2, 0)


def inspect_file(path):
    path=Path(path);data=path.read_bytes();header,root=container(data)
    records=graph_records(data)
    graphs=[graph_summary(raw)for kind,raw in records if kind=='ordinary']
    composites=[graph_summary(raw)for kind,raw in records if kind=='composite']
    signals=[];mounts=[];diagnostics=[]
    for section in vals(root,10):
        fs=fields(section)
        for meta in vals(fs,5):
            for signal in vals(fields(meta),3):
                text=unique(fields(signal),3)
                if text:signals.append(text.decode('utf-8',errors='replace'))
    for group in (vals(root,5) if path.suffix.lower()!='.gia' else []):
        for entity in vals(fields(group),1):
            ef=fields(entity);eid=unique(ef,1,0)
            mounts.extend({'entity_id':eid,'graph_id':gid} for gid in entity_graph_ids(entity) if gid is not None)
    for script_group in vals(root,50):
        for entry in vals(fields(script_group),1):
            ef=fields(entry)
            if unique(ef,3) is None or unique(ef,5) is None:diagnostics.append('Unrecognized script entry layout')
    from level_authoring import inspect_bindings
    client_bindings=inspect_bindings(data) if path.suffix.lower()!='.gia' else None
    counts=collections.Counter(n for n,_,_,_ in root)
    return {'file':str(path.resolve()),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
            'header':list(header),'top_level_counts':dict(counts),'graphs':graphs,'composite_graphs':composites,
            'stored_nodes':sum(g['stored_nodes'] for g in graphs),'signals':signals,'mounts':mounts,
            'client_bindings':client_bindings,'script_entries':sum(len(vals(fields(v),1)) for v in vals(root,50)),
            'diagnostics':diagnostics,'editor_expanded_nodes':None,'host_validated':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out')
    a=p.parse_args();src=Path(a.input)
    paths=sorted(src.glob('*.gil'))+sorted(src.glob('*.gia')) if src.is_dir() else [src]
    reports=[]
    for path in paths:
        try:reports.append(inspect_file(path))
        except (ValueError,OSError) as exc:reports.append({'file':str(path.resolve()),'error':str(exc)})
    output={'schema':'qianxing-inspect/v2','files':reports} if src.is_dir() else {'schema':'qianxing-inspect/v2',**reports[0]}
    if a.out:
        with Path(a.out).open('x',encoding='utf-8') as f:json.dump(output,f,ensure_ascii=False,indent=2)
    print(json.dumps(output,ensure_ascii=False,indent=2))
    return 1 if any('error' in r for r in reports) else 0
if __name__=='__main__':raise SystemExit(main())
