"""Explicit local installation step; never executed implicitly by an MCP query."""
from pathlib import Path
import argparse,json,subprocess,sys,os,hashlib
from runtime_policy import PYTHON_RANGE,supported_python

def configure(python,destination,project,outputs,config,resume=False):
    python=Path(python).resolve(strict=True);destination=Path(destination).resolve()
    project=Path(project).resolve(strict=True);outputs=Path(outputs).resolve()
    config=Path(config).resolve()
    requirements=Path(__file__).resolve().parent/'runtime-requirements.lock'
    binding={'python':str(python),'project':str(project),'outputs':str(outputs),'config':str(config),
             'lock_sha256':hashlib.sha256(requirements.read_bytes()).hexdigest()}
    journal=destination/'.installation-pending.json'
    if destination.exists():
        if not resume or config.exists() or not journal.is_file() or json.loads(journal.read_text())!=binding:
            raise ValueError('Runtime exists; resume requires a matching unfinished installation')
    elif resume:raise ValueError('No unfinished runtime to resume')
    if project.is_relative_to(outputs) or outputs.is_relative_to(project):raise ValueError('Project and output roots must be disjoint')
    version=json.loads(subprocess.check_output([str(python),'-c','import sys,json;print(json.dumps(list(sys.version_info[:2])))'],text=True))
    if not supported_python(version):raise ValueError(f'Locked dependencies require CPython {PYTHON_RANGE}')
    destination.mkdir(parents=True,exist_ok=True)
    journal.write_text(json.dumps(binding),encoding='utf-8')
    subprocess.run([str(python),'-m','venv',str(destination)],check=True)
    exe=destination/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    subprocess.run([str(exe),'-m','pip','install','--disable-pip-version-check','--require-hashes','--only-binary=:all:','-r',str(requirements)],check=True)
    subprocess.run([str(exe),'-c','import mcp,lupa.lua53,PIL'],check=True)
    lock=subprocess.check_output([str(exe),'-m','pip','freeze','--all'],text=True)
    (destination/'installed-requirements.lock').write_text(lock,encoding='utf-8')
    outputs.mkdir(parents=True,exist_ok=True);config=Path(config).resolve();config.parent.mkdir(parents=True,exist_ok=True)
    record={'schema':1,'python':str(exe),'project_root':str(project),'output_root':str(outputs),'requirements_lock':str(destination/'installed-requirements.lock')}
    temporary=config.with_suffix('.pending');temporary.write_text(json.dumps(record,indent=2),encoding='utf-8');temporary.replace(config)
    journal.unlink()
    print(json.dumps(record));return record

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--python',required=True);p.add_argument('--runtime',required=True);p.add_argument('--project',required=True);p.add_argument('--outputs',required=True);p.add_argument('--config',required=True);p.add_argument('--resume',action='store_true');a=p.parse_args();configure(a.python,a.runtime,a.project,a.outputs,a.config,a.resume)
