"""Stage and evidence checks exclusively for Genshin Qianxing UGC production."""
from pathlib import Path
import argparse,hashlib,json,re,sys
from authoring_io import read_json, sha_file

DOMAIN='genshin-qianxing-ugc'
PHASES={
 'feature':['inspect','design','plan','slice','implement','review','build','playtest','deliver'],
 'fix':['inspect','reproduce','diagnose','plan','implement','regression','review','build','playtest','deliver'],
 'ui':['inspect','interaction','plan','implement','layout_review','build','playtest','deliver'],
 'assets':['inspect','choose_output','generate','visual_review','integrate','deliver'],
 'delivery':['inspect','lineage','plan','assemble','readback','playtest','deliver']}
PURPOSE={
 'inspect':'读取当前奇域源码、模板/GIL、映射与保留项',
 'design':'明确玩法循环、胜败、权威状态与设备输入',
 'plan':'按依赖拆分实际文件、负责技能和验收条件',
 'slice':'先完成进入、首轮操作、结果与重开的最小闭环',
 'implement':'编写并连接实际图、Lua、协议和必要资源',
 'review':'按需求覆盖、接口、类型、生命周期与预算分别复核',
 'build':'严格编译并整合GIA/GIL，核对输入来源及回读',
 'playtest':'按真实玩家路径检查操作反馈、输入边界、重开和目标设备，并分层保存证据',
 'deliver':'交付当前文件、证据和未验收项，保留用户基底',
 'reproduce':'记录触发、预期、实际结果和对应交付摘要',
 'diagnose':'逐项验证假设，定位输入/状态/执行/渲染/原生环节',
 'regression':'验证原失败路径及相邻功能，记录仍无法复现之处',
 'interaction':'明确控件显示、命中、输入屏蔽与设备适配',
 'layout_review':'核对实际布局、长文本、预算和设备证据',
 'choose_output':'按宿主需要选择矩形、富文本或适用拟合',
 'generate':'生成可接入数据与参考预览，保留源摘要',
 'visual_review':'检查透明边缘、图层、颜色与实际输出预算',
 'integrate':'接入真实模板、控件池、动画或整合文件',
 'lineage':'确认源码、生成物、图和报告属于同一版本',
 'assemble':'按依赖顺序写信号、图、Lua及资源',
 'readback':'核对实际脚本、定义、连接、挂载与字段保护'}
def guide(kind='feature'):
 if kind not in PHASES:raise ValueError('Unknown Qianxing task kind')
 return {'domain':DOMAIN,'kind':kind,'phases':[{'id':p,'exit_condition':PURPOSE[p]} for p in PHASES[kind]],'approval_policy':'Proceed within existing authorization; ask only for unavailable essential inputs or material gameplay choices.','automatic_gameplay_validation':False,'experience_checklist':['player_verbs_and_feedback','simulation_presentation_ownership','input_action_and_modal_boundaries','HUD_and_playfield_readability','asset_canvas_scale_anchor','session_end_restart_and_reentry']}


def check_production_report(report_path):
    from portable_trust import listed_path

    report = Path(report_path).resolve()
    data = read_json(report)
    if not isinstance(data, dict):
        raise ValueError('Expected actual production report')

    if 'files' in data:
        if data.get('schema') != 2 or data.get('kind') != 'production':
            raise ValueError('Expected actual production report')
        files = data['files']
        evidence = data.get('evidence')
        if not files:
            raise ValueError('Production report lists no artifacts')
    else:
        files = data.get('files_sha256')
        evidence = data.get('evidence', {})
    if not isinstance(files, dict) or not isinstance(evidence, dict):
        raise ValueError('Expected actual production report')

    checked = set()
    for name, digest in files.items():
        path = listed_path(report.parent, name, checked)
        if not path.is_file() or sha_file(path) != digest:
            raise ValueError('Production artifact missing/stale: ' + name)
    for stage, entry in evidence.items():
        if not isinstance(entry, dict) or entry.get('status') not in (
            'passed', 'failed', 'not_checked', 'not_applicable',
        ):
            raise ValueError('Invalid production stage evidence: ' + stage)
        if entry['status'] == 'failed':
            raise ValueError('Production report contains a failed stage: ' + stage)
    return evidence


def check(plan_path,report_path=None):
 p=Path(plan_path).resolve();plan=json.loads(p.read_text(encoding='utf-8-sig'))
 if not isinstance(plan,dict) or set(plan)-{'schema','domain','kind','goal','requirements','steps'}:raise ValueError('Invalid workflow fields')
 if plan.get('schema')!=1 or type(plan.get('schema'))!=int or plan.get('domain')!=DOMAIN:raise ValueError('Workflow serves Genshin Qianxing UGC only')
 kind=plan.get('kind');guide(kind)
 if not isinstance(plan.get('goal'),str) or not plan['goal'].strip():raise ValueError('Missing Qianxing production goal')
 reqs=plan.get('requirements');steps=plan.get('steps')
 if not isinstance(reqs,list) or not reqs or not isinstance(steps,list) or not steps:raise ValueError('Requirements and production steps required')
 wanted=set()
 for q in reqs:
  if not isinstance(q,dict) or set(q)!={'id','acceptance'} or not isinstance(q['id'],str) or not q['id'] or q['id'] in wanted or not isinstance(q['acceptance'],str) or not q['acceptance'].strip():raise ValueError('Invalid or duplicate acceptance requirement')
  wanted.add(q['id'])
 from capability_index import resolve_owner
 owners={}
 seen={};covered=set();completed=[];blocked=[];proofs=0;previous=-1
 for step in steps:
  if not isinstance(step,dict) or set(step)-{'id','phase','owner','requires','requirements','status','evidence','blocker'}:raise ValueError('Invalid production step fields')
  sid=step.get('id');phase=step.get('phase');status=step.get('status','pending')
  if not isinstance(sid,str) or not sid or sid in seen or phase not in PHASES[kind] or not isinstance(step.get('owner'),str) or status not in ('pending','done','blocked'):raise ValueError('Invalid production step identity/phase/owner/status')
  owners[sid]=resolve_owner(step['owner'])
  order=PHASES[kind].index(phase)
  if order<previous:raise ValueError('Production phases must follow dependency order')
  previous=order;deps=step.get('requires',[]);coverage=step.get('requirements',[])
  if not isinstance(deps,list) or any(not isinstance(x,str) or x not in seen for x in deps):raise ValueError('Dependency missing or not earlier in the plan')
  if not isinstance(coverage,list) or any(not isinstance(x,str) or x not in wanted for x in coverage):raise ValueError('Unknown acceptance requirement')
  covered.update(coverage)
  if status=='done':
   if any(seen[x]!='done' for x in deps):raise ValueError('Completed step depends on unfinished work')
   evidence=step.get('evidence')
   if not isinstance(evidence,list) or not evidence:raise ValueError('Completed stage requires evidence')
   for e in evidence:
    if not isinstance(e,dict) or set(e)!={'kind','path','sha256'} or e['kind'] not in ('source','static','simulation','editor','host'):raise ValueError('Invalid evidence descriptor')
    if not isinstance(e['path'],str) or not isinstance(e['sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',e['sha256']):raise ValueError('Invalid evidence path/hash')
    f=(p.parent/e['path']).resolve()
    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=e['sha256']:raise ValueError('Evidence missing or stale: '+e['path'])
    proofs+=1
   completed.append(sid)
  elif status=='blocked':
   if not isinstance(step.get('blocker'),str) or not step['blocker'].strip():raise ValueError('Blocked stage requires a concrete missing input')
   blocked.append({'id':sid,'reason':step['blocker']})
  seen[sid]=status
 if covered!=wanted:raise ValueError('Acceptance requirement has no implementation/check task: '+repr(sorted(wanted-covered)))
 production=check_production_report(report_path) if report_path else None
 return {'schema':1,'domain':DOMAIN,'kind':kind,'plan_integrity_verified':True,'requirements_traced':len(wanted),'declared_complete_steps':completed,'pending_steps':[s for s,v in seen.items() if v=='pending'],'blocked_steps':blocked,'evidence_hashes_verified':proofs,'production_evidence':production,'gameplay_semantics_verified':False,'evidence_claims_independently_observed':False,'resolved_owners':owners}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='op',required=True)
 g=sub.add_parser('guide');g.add_argument('--kind',choices=list(PHASES),default='feature')
 c = sub.add_parser('check')
 c.add_argument('plan')
 c.add_argument(
     '--report', metavar='FILE',
     help='Check artifact hashes and stage evidence in a production manifest or report',
 )
 test=sub.add_parser('playtest');test.add_argument('--device',choices=['pc','mobile','both'],default='both');test.add_argument('--multiplayer',action='store_true');test.add_argument('--persistence',action='store_true');test.add_argument('--report')
 a=p.parse_args(argv)
 try:
  if a.op=='playtest':
   from qianxing_playtest import matrix,verify
   v=verify(a.report) if a.report else matrix(a.device,a.multiplayer,a.persistence)
  else:v=guide(a.kind) if a.op=='guide' else check(a.plan,a.report)
  print(json.dumps(v,ensure_ascii=False,indent=2));return 1 if v.get('release_blocked') else 0
 except (ValueError,OSError,TypeError,KeyError) as e:print(str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
