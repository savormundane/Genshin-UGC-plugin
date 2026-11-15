"""Read-only source/artifact guards, impact selection and isolated production rebuild."""
from pathlib import Path
import argparse,json,tempfile,shutil
from authoring_io import *

def verify(root,rebuild=False,portable=False):
    root=Path(root).resolve();report=read_json(root/'manifest.json');changed=[];missing=[]
    for name,digest in report['files'].items():
        if name=='manifest.json':continue
        p=root/name
        if not p.is_file():missing.append(name)
        elif sha(p.read_bytes())!=digest:changed.append(name)
    source_changes=[]if portable else[p for p,digest in report['inputs'].items()if not Path(p).is_file()or sha(Path(p).read_bytes())!=digest]
    result={'schema':2,'artifact_changes':changed,'missing':missing,'source_changes':source_changes,'passed':not(changed or missing or source_changes),'rebuild':'not_checked','editor':'not_checked','host':'not_checked'}
    if portable:
        if report.get('portable',{}).get('schema')!=1 or report['portable'].get('root')!='portable':raise ValueError('Production did not include a portable input closure')
        bundle=read_json(root/'portable/portable.json')
        if bundle.get('schema')!=1:raise ValueError('Unknown portable input schema')
        for name,digest in bundle['files'].items():
            p=root/'portable'/name
            if not p.is_file()or sha(p.read_bytes())!=digest:result['passed']=False;changed.append('portable/'+name)
        result['source_check']='packaged_inputs';rebuild=True
    if rebuild:
        if not result['passed']:raise ValueError('Stale source/artifact; do not re-sign old evidence')
        if report.get('kind')!='production':raise ValueError('Rebuild requires production manifest')
        from production_core import produce
        with tempfile.TemporaryDirectory(prefix='qianxing-rebuild-')as td:
            target=Path(td)/'result'
            if portable:
                from portable_delivery import execute
                bundle=Path(td)/'portable';shutil.copytree(root/'portable',bundle)
                result['portable_execution']=execute(bundle,target)
            else:produce(report['specification'],target)
            if 'artifacts'in report:
                from delivery_artifacts import compare
                before=report['artifacts'];after=read_json(target/'manifest.json')['artifacts']
                if set(before)!=set(report['files']):raise ValueError('Artifact roles do not cover the manifest')
                if portable:before={name:item for name,item in before.items()if item['role']!='input_snapshot'}
                comparison=compare(before,after,root,target)
                differences=comparison['differences']+comparison['role_changes'];count=comparison['compared']
                result['comparison_scope']='delivery_roles';result['role_changes']=comparison['role_changes']
            else:
                # Historical schema-2 manifests retain their original scope.
                artifacts=[name for name in report['files']if Path(name).suffix.lower()in('.lua','.gil','.gia','.png')]
                differences=[name for name in artifacts if not(target/name).is_file()or (root/name).read_bytes()!=(target/name).read_bytes()];count=len(artifacts)
                result['comparison_scope']='legacy_suffixes'
            result.update(rebuild='failed'if differences else'passed',rebuild_artifacts=count,rebuild_differences=differences,passed=not differences)
    return result
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--rebuild',action='store_true');p.add_argument('--portable',action='store_true');p.add_argument('--out');a=p.parse_args(argv);r=verify(a.output,a.rebuild,a.portable)
    if a.out:
        with Path(a.out).open('x',encoding='utf-8')as f:json.dump(r,f,ensure_ascii=False,indent=2)
    print(json.dumps(r,ensure_ascii=False));return 0 if r['passed']else 2
