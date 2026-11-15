"""Detect undeclared Python file inputs in trusted portable builds, not an OS sandbox."""
from pathlib import Path
import json,os,runpy,sys

def main():
    boundary=json.loads(os.environ['UGC_BUILD_BOUNDARY'])
    allowed=[Path(p).resolve()for p in boundary['read_roots']]
    writable=[Path(p).resolve()for p in boundary.get('write_roots',[])]
    seen=set()
    def audit(event,args):
        if event not in ('open','os.listdir','os.scandir'):return
        value=args[0]
        if value is None or isinstance(value,int):return
        path=Path(os.fsdecode(value)).resolve()
        if str(path).casefold()==os.devnull.casefold():return
        if event=='open'and args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            if not any(path.is_relative_to(root)for root in writable):raise ValueError('Write outside portable output/scratch: '+str(path))
            if args[2]&os.O_WRONLY:return
        if not any(path.is_relative_to(root)for root in allowed):
            raise ValueError('Undeclared portable input: '+str(path))
        if event=='open':seen.add(str(path))
    sys.addaudithook(audit)
    args=sys.argv[1:]
    try:
        if args[0]=='-m':
            sys.argv=args[1:];sys.path.insert(0,str(Path.cwd()));runpy.run_module(args[1],run_name='__main__',alter_sys=True)
        else:
            script=Path(args[0]).resolve();sys.argv=[str(script),*args[1:]];sys.path.insert(0,str(script.parent));runpy.run_path(str(script),run_name='__main__')
    finally:
        dest=Path(boundary['trace'])/(str(os.getpid())+'.json')
        dest.write_text(json.dumps(sorted(seen),ensure_ascii=False),encoding='utf-8')

if __name__=='__main__':main()
