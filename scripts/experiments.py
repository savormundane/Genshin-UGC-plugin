"""Lua model experiments with immutable seed splits, paired observations and failures."""
from pathlib import Path
import argparse,json,time
from authoring_io import *
from joint_simulator import run as simulate

def execute(spec,base):
    schema(spec,('schema','source','entry','development_seeds','holdout_seeds','split','policies','metrics','tuning'),('source','entry','development_seeds','holdout_seeds','split','policies','metrics'))
    dev=spec['development_seeds'];hold=spec['holdout_seeds']
    if len(set(dev+hold))!=len(dev+hold)or any(type(s)!=int for s in dev+hold):raise ValueError('Seed splits must be unique disjoint integer lists')
    if spec['split']not in('development','holdout')or spec['split']=='holdout'and spec.get('tuning',False):raise ValueError('Holdout cannot be used for tuning')
    if not(dev if spec['split']=='development'else hold)or not spec['policies']or not spec['metrics']:raise ValueError('A nonempty seed split, policies and metrics are required')
    if len({canonical(p)for p in spec['policies']})!=len(spec['policies'])or len(set(spec['metrics']))!=len(spec['metrics']):raise ValueError('Duplicate policies or observation metrics')
    rows=[];path=resolve(base,spec['source']);inputs={str(path):sha(path.read_bytes())}
    for seed in dev if spec['split']=='development'else hold:
        for policy in spec['policies']:
            scene={'schema':2,'clients':[{'id':1,'source':str(path)}],'steps':[{'op':'invoke','client':1,'name':spec['entry'],'args':[seed,policy]}],'observations':[{'client':1,'path':m,'name':m}for m in spec['metrics']]}
            started=time.perf_counter()
            try:result=simulate(scene,base);row={'seed':seed,'policy':policy,'passed':True,'metrics':result['observations']}
            except ValueError as e:row={'seed':seed,'policy':policy,'passed':False,'error':str(e),'failure_trace':getattr(e,'detail',None),'invocation':scene['steps'][0]}
            row['model_seconds']=time.perf_counter()-started;rows.append(row)
    return {'schema':2,'inputs':inputs,'split':spec['split'],'seed_sets':{'development':dev,'holdout':hold},'rows':rows,'passed':all(r['passed']for r in rows),'host_tested':False,'timing_kind':'interpreter elapsed; not host FPS or human duration'}
def compare(a,b):
    if a['split']!=b['split']or a['seed_sets']!=b['seed_sets']:raise ValueError('Paired seed sets differ')
    key=lambda r:(r['seed'],canonical(r['policy']));left={key(r):r for r in a['rows']};right={key(r):r for r in b['rows']}
    if len(left)!=len(a['rows'])or len(right)!=len(b['rows']):raise ValueError('Duplicate paired observations')
    if set(left)!=set(right):raise ValueError('Paired policies/cases differ')
    rows=[]
    for k,x in left.items():
        y=right[k];deltas={}
        if x['passed']and y['passed']:
            if set(x['metrics'])!=set(y['metrics']):raise ValueError('Paired observation metrics differ')
            for name,v in x['metrics'].items():
                w=y['metrics'][name]
                if type(v)in(int,float)and type(w)in(int,float):deltas[name]=w-v
        rows.append({'seed':k[0],'policy':x['policy'],'before':x,'after':y,'numeric_deltas':deltas})
    return {'schema':2,'split':a['split'],'rows':rows,'causal_improvement_verified':False,'host_tested':False}
def build(path,out):
    p=Path(path).resolve();r=execute(read_json(p),p.parent)
    with output_directory(out)as stage:
        write_json(stage/'observations.json',r);return finish(stage,{str(p):sha(p.read_bytes()),**r['inputs']},kind='experiment',passed=r['passed'])
def main(argv=None):
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='op',required=True);a=s.add_parser('run');a.add_argument('spec');a.add_argument('--out',required=True)
    a=s.add_parser('compare');a.add_argument('before');a.add_argument('after');a.add_argument('--out',required=True);a=p.parse_args(argv)
    if a.op=='run':r=build(a.spec,a.out)
    else:
        r=compare(read_json(a.before),read_json(a.after))
        with Path(a.out).open('x',encoding='utf-8')as f:json.dump(r,f,ensure_ascii=False,indent=2)
    print(json.dumps(r,ensure_ascii=False));return 0 if r.get('passed',True)else 2
