"""Official ServerSignal types and calibrated server VarType IDs."""
import math
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
