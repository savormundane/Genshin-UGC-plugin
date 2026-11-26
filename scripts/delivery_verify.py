"""Read-only source/artifact guards, impact selection and isolated production rebuild."""
from pathlib import Path
import argparse,json,tempfile,shutil
from authoring_io import DiagnosticError, read_json, sha_file

def verify(root,rebuild=False,portable=False,trusted_inputs_sha256=None,*,artifacts_only=False):
    from portable_trust import listed_path, closure, trusted_execution
    if artifacts_only and (portable or rebuild or trusted_inputs_sha256 is not None):
        raise ValueError('Artifact-only verification cannot be combined with portable input verification or rebuild')
    root = Path(root).absolute()
    checked = set()
    report = read_json(listed_path(root, 'manifest.json', checked))
    if not isinstance(report, dict):
        raise ValueError('交付清单必须是工具生成的 JSON 对象。')
    checksums = report.get('files')
    if checksums is None and type(report.get('schema')) is int and report['schema'] == 1:
        checksums = report.get('files_sha256')
        if isinstance(checksums, dict) and not artifacts_only:
            raise DiagnosticError(
                'verify.artifacts_only_required',
                '此版素材清单仅登记产物校验值。请在 MCP 调用中设置 artifacts_only=true，'
                '或在终端添加 --artifacts-only。',
            )
    if not isinstance(checksums, dict):
        raise ValueError('交付清单缺少产物校验值。请提供工具生成的 manifest.json。')
    changed, missing = [], []
    for name,digest in checksums.items():
        if name=='manifest.json':continue
        p=listed_path(root,name,checked)
        if not p.is_file():missing.append(name)
        elif sha_file(p)!=digest:changed.append(name)
    source_changes=[]
    source_check='not_checked'
    if not (portable or artifacts_only):
        source_changes=[p for p,digest in report['inputs'].items()if not Path(p).is_file()or sha_file(p)!=digest]
        source_check='failed' if source_changes else 'passed'
    result={'schema':2,'scope':'artifacts_only' if artifacts_only else 'portable' if portable else 'sources_and_artifacts',
            'artifact_check':'failed' if changed or missing else 'passed',
            'artifact_changes':changed,'missing':missing,'source_check':source_check,'source_changes':source_changes,
            'passed':not(changed or missing or source_changes),'rebuild':'not_checked','editor':'not_checked','host':'not_checked'}
    if portable:
        import os
        for directory,dirs,files in os.walk(root,followlinks=False):
            for name in dirs+files:
                item=Path(directory)/name;relative=item.relative_to(root).as_posix();listed_path(root,relative,checked)
                if item.is_file() and relative!='manifest.json' and relative not in checksums:
                    raise ValueError('Unregistered delivery input: '+relative)
        if report.get('portable',{}).get('schema')!=1 or report['portable'].get('root')!='portable':raise ValueError('Production did not include a portable input closure')
        _, token = closure(root/'portable')
        result['source_check']='packaged_inputs'
        result['trusted_inputs_sha256']=token
        result['execution_boundary']='Static checks do not authorize project code execution'
    if rebuild:
        if not portable:raise ValueError('Explicit rebuild requires portable input closure and trusted_inputs_sha256; use --portable')
        if not result['passed']:raise ValueError('Stale source/artifact; do not re-sign old evidence')
        if report.get('kind')!='production':raise ValueError('Rebuild requires production manifest')
        trusted_execution(root/'portable',trusted_inputs_sha256)
        with tempfile.TemporaryDirectory(prefix='qianxing-rebuild-')as td:
            target=Path(td)/'result'
            from portable_delivery import execute
            bundle=Path(td)/'portable';shutil.copytree(root/'portable',bundle)
            result['portable_execution']=execute(bundle,target,trusted_inputs_sha256)
            if 'artifacts'in report:
                from delivery_artifacts import compare
                before=report['artifacts'];after=read_json(target/'manifest.json')['artifacts']
                if set(before)!=set(checksums):raise ValueError('Artifact roles do not cover the manifest')
                if portable:before={name:item for name,item in before.items()if item['role']!='input_snapshot'}
                comparison=compare(before,after,root,target)
                differences=comparison['differences']+comparison['role_changes'];count=comparison['compared']
                result['comparison_scope']='delivery_roles';result['role_changes']=comparison['role_changes']
            else:
                # Historical schema-2 manifests retain their original scope.
                artifacts=[name for name in checksums if Path(name).suffix.lower()in('.lua','.gil','.gia','.png')]
                differences=[name for name in artifacts if not(target/name).is_file()or (root/name).read_bytes()!=(target/name).read_bytes()];count=len(artifacts)
                result['comparison_scope']='legacy_suffixes'
            result.update(rebuild='failed'if differences else'passed',rebuild_artifacts=count,rebuild_differences=differences,passed=not differences)
    return result
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--rebuild',action='store_true');p.add_argument('--portable',action='store_true');p.add_argument('--artifacts-only',action='store_true');p.add_argument('--trusted-inputs-sha256');p.add_argument('--out');a=p.parse_args(argv);r=verify(a.output,a.rebuild,a.portable,a.trusted_inputs_sha256,artifacts_only=a.artifacts_only)
    if a.out:
        with Path(a.out).open('x',encoding='utf-8')as f:json.dump(r,f,ensure_ascii=False,indent=2)
    print(json.dumps(r,ensure_ascii=False));return 0 if r['passed']else 2
