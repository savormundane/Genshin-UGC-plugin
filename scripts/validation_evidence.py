"""Shared validation dependencies and recorded test-case coverage; no environment writes."""
from pathlib import Path
import fnmatch
import importlib.metadata
import importlib.machinery
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
from authoring_io import PLUGIN,inventory,read_json,sha

def contract():
    value=read_json(PLUGIN/'scripts/validation-contract.json')
    if value.get('schema')!=1:raise ValueError('Unknown validation contract schema')
    return value

def runtime_rule(path):
    name=Path(path).as_posix()
    prefix=PLUGIN.as_posix()+'/'
    if name.startswith(prefix):name=name[len(prefix):]
    return any(fnmatch.fnmatchcase(name,pattern) or name.endswith('/'+pattern)
               or '/'not in name and name==Path(pattern).name
               for pattern in contract()['runtime_rules'])

def execution_inventory():
    return {p:h for p,h in inventory(PLUGIN).items()if not p.endswith('.md')or runtime_rule(p)}

def validation_dependencies(root):
    root=Path(root);result={}
    for pattern in contract()['development_inputs']:
        for path in sorted(root.glob(pattern)):
            if path.is_symlink():raise ValueError('Linked validation dependency '+str(path))
            if path.is_file()and '__pycache__'not in path.parts:
                result[path.relative_to(root).as_posix()]=sha(path.read_bytes())
    market=PLUGIN.parent/'.agents/plugins/marketplace.json'
    result['@self-use-marketplace']=sha(market.read_bytes())if market.is_file()else None
    return result

def backend_inventory():
    result={'python':{'version':sys.version,'platform':platform.platform(),'executable':sha(Path(sys.executable).read_bytes())}}
    # Native interpreter/runtime libraries are separate from the executable on Windows.
    runtime=Path(sys.executable).parent
    result['python']['runtime_files']={p.name:sha(p.read_bytes())for pattern in('python*.dll','python*.zip')for p in sorted(runtime.glob(pattern))}
    stdlib=Path(sysconfig.get_path('stdlib'))
    result['python']['stdlib']={p.relative_to(stdlib).as_posix():sha(p.read_bytes())for p in sorted(stdlib.rglob('*.py'))if 'site-packages'not in p.parts}
    result['python']['extensions']={p.name:sha(p.read_bytes())for p in sorted((runtime/'DLLs').glob('*'))if p.is_file()}
    base_runtime=Path(sys.base_prefix)
    result['python']['base_runtime_files']={p.name:sha(p.read_bytes())for pattern in('python*.dll','python*.zip')for p in sorted(base_runtime.glob(pattern))}
    result['python']['base_extensions']={p.name:sha(p.read_bytes())for p in sorted((base_runtime/'DLLs').glob('*'))if p.is_file()}
    result['dependency_versions']={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}
    for name in('lupa','PIL','mcp'):
        spec=importlib.util.find_spec(name)
        if spec is None or not spec.submodule_search_locations:
            result[name]={'available':False};continue
        directory=Path(next(iter(spec.submodule_search_locations)))
        distribution=importlib.metadata.distribution('Pillow'if name=='PIL'else name)
        result[name]={'available':True,'version':distribution.version,'files':inventory(directory)}
    # Some suites explicitly prepend this directory; capture that resolution too.
    override=os.environ.get('UGC_LUA_TEST_PATH')
    if override:
        result['test_path_packages']={}
        for name in('lupa','PIL'):
            spec=importlib.machinery.PathFinder.find_spec(name,[override])
            result['test_path_packages'][name]=inventory(Path(next(iter(spec.submodule_search_locations))))if spec and spec.submodule_search_locations else None
    node=shutil.which('node')
    if node:
        probe=subprocess.run([node,'--version'],capture_output=True,text=True,timeout=10)
        result['node']={'available':probe.returncode==0,'version':probe.stdout.strip(),'executable':sha(Path(node).read_bytes())}
    else:result['node']={'available':False}
    return result

def case_coverage(proof):
    passed={row['test']+'::'+case['id']for row in proof.get('results',[])for case in row.get('cases',[])if case.get('status')=='passed'}
    return {name:{'required':cases,'missing':sorted(set(cases)-passed),
                  'status':'passed'if set(cases)<=passed else'not_checked'}
            for name,cases in contract()['coverage'].items()}
