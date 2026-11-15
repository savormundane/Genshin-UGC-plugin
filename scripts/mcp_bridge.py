"""Fixed operations shared by local MCP and CLI; no arbitrary command tool."""
from pathlib import Path
import argparse,asyncio,json,os,re,sys,tempfile
from authoring_io import PLUGIN,sha,schema,read_json,write_json

OPERATIONS={'doctor':(), 'capabilities':(), 'docs_search':('version','query'),'api_lookup':('symbol',),'diagnose':('spec','sha256'),
            'native_inspect':('input','sha256'),'native_audit':('input','sha256'),
            'project_inspect':('input','sha256'),'client_check':('input','sha256'),
            'native_diff':('input','sha256','other','other_sha256'),
            'native_plan':('input','sha256','spec','spec_sha256','output'),
            'simulate':('spec','sha256','output'),'experiment_run':('spec','sha256','output'),
            'experiment_compare':('input','sha256','other','other_sha256'),
            'logs_diagnose':('spec','sha256'),'verify':('input','sha256','rebuild','portable'),
            'produce':('spec','sha256','output'),'native_apply':('input','sha256','plan','plan_sha256','output')}


class Bridge:
    def __init__(self,project,output_root):
        self.project=Path(project).resolve(strict=True);self.output_root=Path(output_root).resolve(strict=True)
        if not self.project.is_dir()or not self.output_root.is_dir():raise ValueError('Project/output roots must be directories')
        if self.project.is_relative_to(self.output_root)or self.output_root.is_relative_to(self.project):raise ValueError('Project and output roots must be disjoint')
        if self.output_root.is_relative_to(PLUGIN)or PLUGIN.is_relative_to(self.output_root):raise ValueError('Output root overlaps plugin source')

    def path(self,value,output=False):
        if not isinstance(value,str)or not value:raise ValueError('Nonempty path required')
        root=self.output_root if output else self.project
        original=Path(os.path.abspath(root/value));resolved=original.resolve()
        owners=[r for r in ([self.output_root]if output else[self.project,self.output_root])if resolved.is_relative_to(r)]
        if not owners or resolved in owners:raise ValueError('Path outside allowed project/output roots')
        owner=max(owners,key=lambda p:len(p.parts))
        for part in(original,*original.parents):
            if part==owner:break
            if part.is_symlink()or getattr(part,'is_junction',lambda:False)():raise ValueError('Linked tool path refused')
        if output:
            if resolved.exists():raise ValueError('Output exists; choose a new directory')
            if not resolved.parent.is_dir():raise ValueError('Output parent must exist')
        elif not resolved.is_file():raise ValueError('Input file missing')
        return resolved

    async def call(self,operation,arguments,progress=None):
        if operation not in OPERATIONS:raise ValueError('Unknown bridge operation')
        allowed=OPERATIONS[operation]+(('contract','contract_sha256')if operation=='client_check'else())
        schema(arguments,allowed,OPERATIONS[operation]);args=dict(arguments);bound={}
        if ('contract'in args)!=('contract_sha256'in args):raise ValueError('Contract requires digest')
        for field,digest_field in(('input','sha256'),('spec','spec_sha256'if operation=='native_plan'else'sha256'),('other','other_sha256'),('plan','plan_sha256'),('contract','contract_sha256')):
            if field not in args:continue
            path=self.path(args[field]);digest=args[digest_field]
            if not isinstance(digest,str)or not re.fullmatch('[0-9a-f]{64}',digest)or sha(path.read_bytes())!=digest:raise ValueError('Input digest mismatch: '+field)
            args[field]=str(path);bound[str(path)]=digest
        if operation=='verify'and any(type(args[k])is not bool for k in ('rebuild','portable')):raise ValueError('Verification flags must be boolean')
        destination=self.path(args['output'],True)if 'output'in args else None
        if progress:await progress(0,3,'Inputs bound')
        # Only this request's private directory is removed on failure/cancellation.
        with tempfile.TemporaryDirectory(prefix='qianxing-mcp-',dir=self.output_root)as temporary:
            scratch=Path(temporary);request=scratch/'request.json';result_path=scratch/'result.json'
            if destination:args['output']=str(scratch/'delivery')
            write_json(request,{'operation':operation,'arguments':args,'inputs':bound,'project':str(self.project),
                               'output_root':str(self.output_root),'scratch':str(scratch)})
            process=None
            with (scratch/'stdout.log').open('wb')as stdout,(scratch/'stderr.log').open('wb')as stderr:
                try:
                    process=await asyncio.create_subprocess_exec(sys.executable,'-X','utf8','-B',str(PLUGIN/'scripts/mcp_worker.py'),
                        str(request),str(result_path),cwd=self.project,stdout=stdout,stderr=stderr,
                        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},start_new_session=os.name!='nt')
                    if progress:await progress(1,3,'Core operation running')
                    code=await process.wait()
                finally:
                    if process is not None and process.returncode is None:
                        # Shield cleanup from SDK cancellation; kill descendants too.
                        async def terminate():
                            if os.name=='nt':
                                killer=await asyncio.create_subprocess_exec('taskkill','/PID',str(process.pid),'/T','/F',stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
                                await killer.wait()
                            else:
                                import signal
                                os.killpg(process.pid,signal.SIGKILL)
                            await process.wait()
                        cleanup=asyncio.create_task(terminate())
                        # AnyIO cancellation can interrupt every checkpoint.
                        import anyio
                        with anyio.CancelScope(shield=True):await asyncio.shield(cleanup)
            if code!=0:
                detail=(scratch/'stderr.log').read_text(encoding='utf-8',errors='replace')[-8000:]
                return {'schema':2,'operation':operation,'status':'failed','error':detail,'output':None}
            result=read_json(result_path)
            for path,digest in bound.items():
                if sha(Path(path).read_bytes())!=digest:raise ValueError('Input changed during operation')
            if progress:await progress(2,3,'Core result checked; ready to commit')
            await asyncio.sleep(0)
            status=result.get('status', 'failed'if result.get('passed')is False else'passed')
            if destination and status!='passed':return {'schema':2,'operation':operation,'status':status,'result':result,'output':None}
            if destination:
                self.path(str(destination),True)
                os.rename(scratch/'delivery',destination)
            return {'schema':2,'operation':operation,'status':status,
                    'result':result,'output':str(destination)if destination else None}


def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    for name in('serve','call'):
        command=sub.add_parser(name);command.add_argument('--project',default=os.environ.get('UGC_PROJECT_ROOT'));command.add_argument('--output-root',default=os.environ.get('UGC_OUTPUT_ROOT'))
        if name=='call':command.add_argument('request')
    args=parser.parse_args(argv)
    if not args.project or not args.output_root:parser.error('Explicit project/output roots or UGC_PROJECT_ROOT/UGC_OUTPUT_ROOT required')
    bridge=Bridge(args.project,args.output_root)
    if args.operation=='serve':
        from mcp_service import server
        server(bridge).run(transport='stdio');return 0
    request=read_json(args.request);schema(request,('schema','operation','arguments'),('operation','arguments'))
    result=asyncio.run(bridge.call(request['operation'],request['arguments']))
    print(json.dumps(result,ensure_ascii=False));return 1 if result['status']in('failed','not_checked')else 0
