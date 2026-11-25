"""Scoped server graph node identity remapping using calibrated wire fields."""
from authoring_io import schema
from miliastra.native.core import get,put,slot
from level_inventory import fields,vals
from level_authoring import msg


def remap_nodes(graph,mapping):
    if not isinstance(mapping,list)or not mapping:raise ValueError('Nonempty node remapping required')
    changes={}
    for item in mapping:
        schema(item,('from','to'),('from','to'))
        if any(type(item[k])is not int or not 1<=item[k]<=2147483647 for k in ('from','to')):raise ValueError('Node indices require positive int32')
        if item['from']in changes:raise ValueError('Duplicate remapping source')
        changes[item['from']]=item['to']
    nodes=vals(fields(graph),3);ids=[get(n,1,0)for n in nodes]
    if len(ids)!=len(set(ids))or None in ids:raise ValueError('Ambiguous node identity')
    if set(changes)-set(ids):raise ValueError('Remapping source absent')
    targets=[changes.get(i,i)for i in ids]
    if len(set(targets))!=len(targets):raise ValueError('Node remapping collision')
    # Refuse unknown carriers rather than assuming they cannot reference nodes.
    def known(raw,allowed,context):
        if any((n,w)not in allowed for n,w,v,r in fields(raw)):raise ValueError('Uncalibrated node reference carrier: '+context)
    def rewrite(raw,field,fn):
        result=[]
        for n,w,v,r in fields(raw):
            if n==field and w==2:
                changed=fn(v);result.append(r if changed==v else msg(n,changed))
            else:result.append(r)
        return b''.join(result)
    def index(raw):
        known(raw,{(1,0),(2,0)},'pin index')
        if get(raw,1,0,0)not in(1,2,3,4):raise ValueError('Only server flow/data indices can be remapped')
    def connection(raw):
        known(raw,{(1,0),(2,2),(3,2)},'connection')
        old=get(raw,1,0)
        if old not in ids:raise ValueError('Dangling node connection')
        for field in(2,3):
            value=get(raw,field)
            if value is not None:index(value)
        return put(raw,1,changes[old],0)if old in changes and changes[old]!=old else raw
    def pin(raw):
        known(raw,{(1,2),(2,2),(3,2),(4,0),(5,2),(7,0)},'node pin')
        for field in(1,2):
            value=get(raw,field)
            if value is not None:index(value)
        return rewrite(raw,5,connection)
    def node(raw):
        known(raw,{(1,0),(2,2),(3,2),(4,2),(5,5),(6,5),(7,2),(9,0),(10,2)},'node')
        for field in(2,3):
            value=get(raw,field)
            if value is not None:
                known(value,{(1,0),(2,0),(3,0),(5,0)},'node property')
                if get(value,2,0,20000)!=20000:raise ValueError('Only server node properties can be remapped')
        old=get(raw,1,0);raw=rewrite(raw,4,pin)
        return put(raw,1,changes[old],0)if old in changes and changes[old]!=old else raw
    def interface(raw):
        known(raw,{(1,2),(2,0),(3,2),(4,2)},'composite interface')
        for field in(1,3,4):
            value=get(raw,field)
            if value is not None:index(value)
        old=get(raw,2,0)
        if old not in ids:raise ValueError('Dangling composite node reference')
        return put(raw,2,changes[old],0)if old in changes and changes[old]!=old else raw
    known(graph,{(1,2),(2,2),(3,2),(4,2),(5,2),(6,2),(100,0),(101,5)},'graph')
    locator=get(graph,1,default=b'');known(locator,{(1,0),(2,0),(3,0),(5,0)},'graph locator')
    if get(locator,2,0,20000)!=20000:raise ValueError('Only server graphs can be remapped')
    return rewrite(rewrite(graph,3,node),4,interface)
