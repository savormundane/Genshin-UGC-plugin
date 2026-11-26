"""Official ServerSignal types and calibrated server VarType IDs."""
import math
import re

from authoring_io import require_fields

TYPES={
 'integer':('整数',3,'AddInt'),'number':('浮点数',5,'AddFloat'),'boolean':('布尔值',4,'AddBool'),'string':('字符串',6,'AddString'),
 'vector3':('三维向量',12,'AddVector3'),'guid':('GUID',2,'AddGuid'),'entity':('实体',1,'AddEntity'),'prefab_id':('元件ID',21,'AddPrefabId'),'config_id':('配置ID',20,'AddConfigId')}
for name,ident in [('integer',8),('number',10),('boolean',9),('string',11),('vector3',15),('guid',7),('entity',13),('prefab_id',23),('config_id',22)]:
    cn,_,method=TYPES[name];TYPES[name+'_list']=(cn+'列表',ident,method+'List')
def valid(kind,value):
    if kind.endswith('_list'):return isinstance(value,list) and all(valid(kind[:-5],v) for v in value)
    if kind=='boolean':return type(value)==bool
    if kind=='string':return isinstance(value,str)
    if kind=='vector3':return isinstance(value,dict) and set(value)=={'x','y','z'} and all(valid('number',v) for v in value.values())
    if kind=='number':return type(value) in (int,float) and math.isfinite(value)
    return type(value)==int and (-2**31<=value<2**31 if kind=='integer' else 0<=value<2**63)


def validate_protocol(spec):
    """Validate the authored signal contract consumed by Lua and native generation."""
    require_fields(spec, ('schema', 'signals'), ('schema', 'signals'))
    if (
        type(spec['schema']) != int
        or spec['schema'] not in (1, 2)
        or not isinstance(spec['signals'], list)
    ):
        raise ValueError('Invalid protocol schema')
    names = set()
    for signal in spec['signals']:
        require_fields(
            signal,
            ('name', 'direction', 'fields', 'phases')
            + (('policy', 'target') if spec['schema'] == 2 else ()),
            ('name', 'direction', 'fields', 'phases'),
        )
        if spec['schema'] == 2 and signal.get('policy') not in ('ordered', 'snapshot'):
            raise ValueError('schema 2 requires ordered/snapshot policy')
        name = signal['name']
        if (
            not isinstance(name, str)
            or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', name)
            or name in names
        ):
            raise ValueError('Invalid or duplicate signal name')
        names.add(name)
        if signal['direction'] not in ('client_to_server', 'server_to_client', 'server_local'):
            raise ValueError('Invalid direction')
        if (
            not isinstance(signal['phases'], list)
            or not signal['phases']
            or len(set(signal['phases'])) != len(signal['phases'])
            or any(not isinstance(p, str) or not p for p in signal['phases'])
        ):
            raise ValueError('Invalid phases')
        if not isinstance(signal['fields'], list):
            raise ValueError('fields must be an ordered list')
        if 'target' in signal:
            target = signal['target']
            if (
                signal['direction'] != 'server_to_client'
                or not isinstance(target, str)
                or target != 'signal_source'
                and not any(
                    target == 'field:' + f['name'] and f['type'] == 'entity'
                    for f in signal['fields']
                )
            ):
                raise ValueError('Client target must be signal_source or an entity field')
        seen = set()
        for f in signal['fields']:
            require_fields(f, ('name', 'type', 'max_length'), ('name', 'type'))
            if not isinstance(f['name'], str) or not f['name'] or f['name'] in seen:
                raise ValueError('Duplicate or invalid parameter')
            seen.add(f['name'])
            if f['type'] not in (
                TYPES if spec['schema'] == 2 else ('integer', 'number', 'boolean', 'string')
            ):
                raise ValueError('Unsupported protocol type')
            if 'max_length' in f and (
                f['type'] != 'string'
                and not f['type'].endswith('_list')
                or type(f['max_length']) != int
                or f['max_length'] < 0
            ):
                raise ValueError('Invalid max_length')
    return spec
