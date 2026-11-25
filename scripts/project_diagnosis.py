"""Explicit read-only diagnostics; never runs production or project code."""
from pathlib import Path
import argparse,json
from authoring_io import schema,read_json,resolve,sha
from evidence_report import finding,manual_records,LAYERS

def diagnose(path):
    path=Path(path).resolve();spec=read_json(path)
    schema(spec,('schema','checks','manual_evidence'),('checks',),version=1)
    if not isinstance(spec['checks'],list) or not spec['checks']:raise ValueError('Explicit nonempty checks required')
    rows=[];details=[];inputs={str(path):sha(path.read_bytes())}
    for check in spec['checks']:
        schema(check,('kind','source','contract','budget'),('kind',))
        kind=check['kind'];source=resolve(path.parent,check['source']) if 'source'in check else None
        if kind not in ('environment','lua','native','asset'):raise ValueError('Unknown diagnostic kind')
        if kind!='environment' and source is None:raise ValueError('Diagnostic source required')
        if source:inputs[str(source)]=sha(source.read_bytes())
        if kind=='environment':
            from capabilities import doctor
            result=doctor();status=result['status']
        elif kind=='lua':
            from miliastra.client.check import inspect
            contract=None
            if 'contract'in check:
                c=resolve(path.parent,check['contract']);inputs[str(c)]=sha(c.read_bytes());contract=read_json(c)
            result=inspect(source,contract=contract);status=result['status']
            from miliastra.client.api import analyze
            if source.suffix.lower()=='.lua' and result['checks']['syntax']=='passed':
                # The contract-aware inspector already resolved and verified bindings.
                analysis=result['scripts'][0]['api'] if contract is not None else analyze(source.read_text(encoding='utf-8-sig'))
                result['api_analysis']=analysis
                if analysis['status']=='failed':status='failed'
                elif analysis['status']=='not_checked' and status!='failed':status='not_checked'
                # AST-located calls in update callbacks, not regex matches in comments.
                import subprocess,shutil
                from authoring_io import PLUGIN
                tree=json.loads(subprocess.check_output([shutil.which('node'),str(PLUGIN/'scripts/client_ast.cjs')],input=source.read_bytes()))
                update_ranges=[];calls=[]
                def walk(node):
                    if isinstance(node,list):
                        for x in node:walk(x)
                    elif isinstance(node,dict):
                        if node.get('type')=='FunctionDeclaration' and (node.get('identifier')or{}).get('name') in ('OnUpdate','OnLevelUpdate'):update_ranges.append(node['range'])
                        if node.get('type')=='CallExpression' and node.get('base',{}).get('type')=='MemberExpression':
                            calls.append({'name':node['base']['identifier']['name'],'range':node['range'],'line':node['loc']['start']['line'],'receiver':'not_inferred_by_performance_rule'})
                        for key,value in node.items():
                            if key not in ('loc','range'):walk(value)
                walk(tree)
                for call in calls:
                    if any(a<=call['range'][0]<b for a,b in update_ranges) and any(token in call['name'] for token in ('Create','Instantiate','Set','Refresh')):
                        rows.append(finding('ui_update_work','warning','not_checked','static',source,call,scope='possible per-frame cost; execution frequency and device performance not measured'))
        elif kind=='native':
            from miliastra.native.core import audit
            result=audit(source.read_bytes());status=result['status']
        else:
            from miliastra.assets.inspection import inspect
            result=inspect(source);status=result['status']
        if 'budget'in check:
            schema(check['budget'],('controls',),('controls',));budget=check['budget']['controls']
            if type(budget)is not int or budget<1:raise ValueError('Positive project control budget required')
            count=result.get('controls')
            rows.append(finding('project_budget','warning','not_checked' if not isinstance(count,int) else 'passed' if count<=budget else 'failed','static',source,{'count':count,'budget':budget},scope='project recommendation, not official hard limit or measured performance'))
        rows.append(finding(kind,'error' if status=='failed' else 'info',status,'static',source or 'environment',{'report_index':len(details)},scope=result.get('scope','explicit check')));details.append(result)
    manual=[]
    if 'manual_evidence'in spec:
        p=resolve(path.parent,spec['manual_evidence']);inputs[str(p)]=sha(p.read_bytes());manual=manual_records(p)
    statuses=[r['status'] for r in rows if r['severity']!='warning']
    status='failed' if 'failed'in statuses else 'not_checked' if 'not_checked'in statuses else 'passed'
    layers={k:'not_checked' for k in LAYERS};layers['static']=status
    return {'schema':1,'status':status,'layers':layers,'findings':rows,'reports':details,'manual_evidence':manual,'inputs':inputs,
            'summary':'\n'.join(f"{r['severity']}: {r['code']} [{r['status']}] {r['subject']}" for r in rows),'scope':'explicit checks only; manual records are separately attributed'}

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('spec');p.add_argument('--format',choices=('json','text'),default='json');a=p.parse_args(argv)
    r=diagnose(a.spec);print(json.dumps(r,ensure_ascii=False,indent=2) if a.format=='json' else r['summary']);return 2 if r['status']=='failed' else 0
