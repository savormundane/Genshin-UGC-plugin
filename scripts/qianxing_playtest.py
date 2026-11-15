"""Qianxing playtest matrix and artifact-bound evidence validation; no GUI automation."""
from pathlib import Path
import hashlib,json,re
DOMAIN='genshin-qianxing-ugc'
BASE_CASES=[
 ('boot','进入后能找到首个可执行操作'),('primary_action','主操作执行正确且显示反馈'),('feedback','输入、状态变化与表现反馈对应'),
 ('result','胜败/结算及取消路径正确'),('restart','重开恢复规则、计时、监听和输入'),('menu_input','菜单显隐与命中、移动/镜头输入边界正确'),
 ('hud','关键信息可读且不遮挡当前主要操作区域'),('assets','素材尺寸、透明、锚点与动作切换稳定'),('budget','初始化和持续更新遵守控件/监听/节点/存档预算')]
def matrix(device='both',multiplayer=False,persistence=False):
 if device not in ('pc','mobile','both'):raise ValueError('Unknown Qianxing device')
 cases=list(BASE_CASES)
 if multiplayer:cases += [('join_sync','参与者进入/离开后状态一致'),('late_packets','重复旧包、乱序与超时按协议处理'),('network_recovery','离线恢复不重复推进或结算')]
 if persistence:cases += [('save_read_failure','首次读档失败不覆盖原档'),('save_confirmation','真实写入并回读后才确认'),('same_level_reentry','退出重进同一发布关卡后保留应保存内容')]
 return {'schema':1,'domain':DOMAIN,'devices':['pc','mobile'] if device=='both' else [device],'cases':[{'id':k,'expected':v,'status':'not_checked'} for k,v in cases],'layers':['static','simulation','editor','host'],'automated_host_playtest':False}
def verify(path):
 p=Path(path).resolve();v=json.loads(p.read_text(encoding='utf-8-sig'))
 if not isinstance(v,dict) or set(v)-{'schema','domain','artifact','device','cases','issues'} or type(v.get('schema'))!=int or v['schema']!=1 or v.get('domain')!=DOMAIN:raise ValueError('Expected Qianxing playtest report')
 if v.get('device') not in ('pc','mobile'):raise ValueError('A report covers one actual device class')
 def evidence(e):
  if not isinstance(e,dict) or set(e)!={'path','sha256','layer'} or e['layer'] not in ('static','simulation','editor','host') or not isinstance(e['path'],str) or not isinstance(e['sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',e['sha256']):raise ValueError('Invalid playtest evidence')
  f=(p.parent/e['path']).resolve()
  if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=e['sha256']:raise ValueError('Playtest evidence missing or stale')
  return e['layer']
 artifact=v.get('artifact')
 if not isinstance(artifact,dict) or set(artifact)!={'path','sha256'}:raise ValueError('Artifact identity required')
 evidence({**artifact,'layer':'static'})
 cases=v.get('cases');issues=v.get('issues',[])
 if not isinstance(cases,list) or not cases or not isinstance(issues,list):raise ValueError('Playtest cases required')
 ids=set();failed=[];pending=[];count=0;host=[]
 for c in cases:
  if not isinstance(c,dict) or set(c)-{'id','status','layer','steps','expected','actual','evidence','reason'}:raise ValueError('Invalid playtest case fields')
  ident=c.get('id');status=c.get('status');layer=c.get('layer')
  if not isinstance(ident,str) or not ident or ident in ids or status not in ('passed','failed','not_checked','not_applicable') or layer not in ('static','simulation','editor','host'):raise ValueError('Invalid case identity/status/layer')
  ids.add(ident)
  if not isinstance(c.get('expected'),str) or not c['expected'].strip():raise ValueError('Expected behavior required')
  if status in ('passed','failed'):
   if not isinstance(c.get('steps'),list) or not c['steps'] or any(not isinstance(x,str) or not x.strip() for x in c['steps']) or not isinstance(c.get('actual'),str) or not c['actual'].strip():raise ValueError('Executed case needs steps and actual result')
   proof=c.get('evidence')
   if not isinstance(proof,list) or not proof:raise ValueError('Executed case needs evidence')
   for e in proof:
    if evidence(e)!=layer:raise ValueError('Evidence layer cannot be promoted')
    count+=1
   if layer=='host':host.append(ident)
   if status=='failed':failed.append(ident)
  else:
   if not isinstance(c.get('reason'),str) or not c['reason'].strip():raise ValueError('Unchecked/inapplicable case needs reason')
   if status=='not_checked':pending.append(ident)
 seen=set();blockers=[]
 for i in issues:
  if not isinstance(i,dict) or set(i)!={'id','severity','case','subsystem','steps','expected','actual'} or i['severity'] not in ('P0','P1','P2','P3') or i['case'] not in ids or i['subsystem'] not in ('rules','input','ui','assets','network','persistence','packaging') or not isinstance(i['id'],str) or not i['id'] or i['id'] in seen:raise ValueError('Invalid playtest issue')
  seen.add(i['id'])
  if not isinstance(i['steps'],list) or not i['steps'] or any(not isinstance(x,str) or not x.strip() for x in i['steps']) or any(not isinstance(i[k],str) or not i[k].strip() for k in ('expected','actual')):raise ValueError('Issue needs reproducible expected/actual behavior')
  if i['severity'] in ('P0','P1'):blockers.append(i['id'])
 return {'domain':DOMAIN,'artifact':artifact,'device':v['device'],'artifact_and_evidence_hashes_verified':True,'verified_evidence_files':count,'failed_cases':failed,'pending_cases':pending,'declared_host_cases':host,'blocking_issues':blockers,'release_blocked':bool(failed or blockers),'gameplay_semantics_verified':False,'host_execution_independently_observed':False}
