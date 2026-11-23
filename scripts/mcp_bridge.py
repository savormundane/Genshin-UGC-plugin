"""Fixed operations shared by local MCP and CLI; no arbitrary command tool."""
from pathlib import Path
import argparse,asyncio,json,os,re,sys,tempfile,math
from authoring_io import DiagnosticError,PLUGIN,sha_file,schema,read_json,write_json

OPERATIONS={'doctor':(), 'capabilities':(), 'docs_search':('version','query'),'api_lookup':('symbol',),'nodes_lookup':(),'resources_lookup':('version',),'diagnose':('spec','sha256'),
            'native_inspect':('input',),'native_audit':('input',),
            'project_inspect':('input',),'client_check':('input',),'graph_check':('input',),
            'native_diff':('input','other'),
            'native_plan':('input','sha256','output'),
            'simulate':('spec','sha256','output'),'experiment_run':('spec','sha256','output'),
            'experiment_compare':('input','sha256','other','other_sha256'),
            'logs_diagnose':('spec','sha256'),'verify':('input','sha256'),
            'produce':('spec','sha256','output'),'native_apply':('input','sha256','plan','plan_sha256','output')}

READ_FILE_OPERATIONS={
    'native_inspect':('sha256',),'native_audit':('sha256',),
    'project_inspect':('sha256','selector','transitive','scope','summary','query','kind','limit'),
    'native_diff':('sha256','other_sha256','allowed_top_level_fields'),
    'client_check':('sha256','contract','contract_sha256','mapping'),
    'graph_check':('sha256','job','job_sha256','bindings','bindings_sha256'),
    'resources_lookup':('query','mode','limit','catalogue','catalogue_sha256'),
}
OPTIONAL_FIELDS={**READ_FILE_OPERATIONS,'native_plan':('patch','spec','spec_sha256','summary'),'produce':('summary',),
                 'nodes_lookup':('query','scope','limit'),'verify':('rebuild','portable','trusted_inputs_sha256','artifacts_only')}
BUILTIN_OPERATIONS = ('doctor', 'capabilities', 'docs_search', 'api_lookup', 'nodes_lookup', 'resources_lookup')


def project_context(project, output_root):
    context = {'project_root': str(project) if project else None,
               'output_root': str(output_root) if output_root else None}
    if not project and not output_root:
        return {**context, 'status': 'unconfigured',
                'message': 'Set UGC_PROJECT_ROOT and UGC_OUTPUT_ROOT to use tools that read or write project files.'}
    if not project or not output_root:
        return {**context, 'status': 'invalid', 'message': 'Both UGC_PROJECT_ROOT and UGC_OUTPUT_ROOT are required.'}
    try:
        project, output_root = Path(project).resolve(strict=True), Path(output_root).resolve(strict=True)
    except (OSError, ValueError, RuntimeError) as exc:
        return {**context, 'status': 'invalid', 'message': 'Cannot resolve project/output roots: ' + str(exc)}
    if not project.is_dir() or not output_root.is_dir():
        message = 'Project/output roots must be directories'
    elif project == Path(project.anchor):
        message = 'Project root must be a specific directory'
    elif project.is_relative_to(output_root) or output_root.is_relative_to(project):
        message = 'Project and output roots must be disjoint'
    elif output_root.is_relative_to(PLUGIN) or PLUGIN.is_relative_to(output_root):
        message = 'Output root overlaps plugin source'
    else:
        return {'status': 'ready', 'project_root': str(project), 'output_root': str(output_root)}
    return {**context, 'status': 'invalid', 'message': message}

async def finish_worker(process):
    """Finish cleanup before releasing the request directory."""
    async def terminate():
        if os.name == 'nt':
            if process.returncode is None:
                killer = await asyncio.create_subprocess_exec(
                    'taskkill', '/PID', str(process.pid), '/T', '/F',
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                try:
                    result = await killer.wait()
                    if result != 0 and process.returncode is None:
                        process.kill()
                finally:
                    if killer.returncode is None:
                        killer.kill()
        else:
            import signal
            try:
                # Startup used a new session. The worker may have exited, leaving its group alive.
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        await process.wait()

    from contextlib import nullcontext
    try:
        from anyio import CancelScope
    except ImportError:
        scope = nullcontext()
    else:
        scope = CancelScope(shield=True)
    with scope:
        cleanup = asyncio.create_task(asyncio.wait_for(terminate(), timeout=15))
        # asyncio callers may cancel again while the independent cleanup task is running.
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        cleanup.result()


class Bridge:
    def __init__(self,project=None,output_root=None):
        self.timeouts = {kind: float(os.environ.get(variable, default)) for kind, variable, default in
                         [('ordinary','UGC_MCP_TIMEOUT_SECONDS','120'),('build','UGC_MCP_BUILD_TIMEOUT_SECONDS','900')]}
        if any(not math.isfinite(value) or not 0 < value <= 3600 for value in self.timeouts.values()):
            raise ValueError('MCP timeouts must be finite seconds in (0, 3600]')
        self.context = project_context(project, output_root)
        self.project = self.output_root = None
        if self.context['status'] == 'ready':
            self.project = Path(self.context['project_root'])
            self.output_root = Path(self.context['output_root'])

    def path(self,value,output=False):
        if self.project is None:
            raise DiagnosticError('mcp.workspace_required', self.context['message'], context=self.context)
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
        build=operation in ('produce','native_apply') or operation=='verify' and arguments.get('rebuild')
        try:
            return await asyncio.wait_for(self._call(operation,arguments,progress),self.timeouts['build' if build else 'ordinary'])
        except asyncio.TimeoutError:
            return {'schema':2,'operation':operation,'status':'failed','error':'MCP operation exceeded its total timeout','output':None}

    async def _call(self,operation,arguments,progress=None):
        if operation not in OPERATIONS:raise ValueError('Unknown bridge operation')
        required=OPERATIONS[operation]
        schema(arguments,required+OPTIONAL_FIELDS.get(operation,()),required)
        args=dict(arguments);bound={};input_hashes={}
        automatic=operation in READ_FILE_OPERATIONS
        builtin = operation in BUILTIN_OPERATIONS and 'catalogue' not in args
        if not builtin and self.project is None:
            raise DiagnosticError('mcp.workspace_required', self.context['message'],
                                  phase=operation, context=self.context)
        if 'summary' in args and type(args['summary']) is not bool:raise ValueError('summary must be a boolean')
        if operation=='native_plan':
            supplied=set(args)&{'patch','spec','spec_sha256'}
            if supplied not in ({'patch'}, {'spec','spec_sha256'}):
                raise ValueError('Provide patch, or provide spec with spec_sha256')
            if 'patch' in args and not isinstance(args['patch'],dict):
                raise ValueError('patch must be a schema 2 object')
        if operation=='project_inspect' and 'transitive' in args:
            if 'selector' not in args or type(args['transitive']) is not bool:
                raise ValueError('transitive requires a selector and a boolean value')
        if operation == 'project_inspect':
            if 'query' in args and ('selector' in args or args.get('summary')):
                raise ValueError('Project search cannot be combined with a selector or summary')
            if 'query' not in args and ('limit' in args or 'kind' in args):
                raise ValueError('Project search kind and limit require a query')
        if 'contract_sha256'in args and 'contract'not in args:raise ValueError('Contract path required')
        if 'mapping'in args and (not isinstance(args['mapping'],str) or not args['mapping']):
            raise ValueError('Nonempty Lua mapping required')
        if 'catalogue_sha256' in args and 'catalogue' not in args:raise ValueError('Catalogue path required')
        if operation=='resources_lookup':
            limit=args.get('limit',20)
            if type(limit) is not int or not 1<=limit<=100:
                raise ValueError('Resource lookup limit must be from 1 to 100')
        digest_fields=(('catalogue','catalogue_sha256'),('input','sha256'),
                       ('spec','spec_sha256' if operation=='native_plan' else 'sha256'),('other','other_sha256'),
                       ('plan','plan_sha256'),('contract','contract_sha256'),('job','job_sha256'),('bindings','bindings_sha256'))
        for field,digest_field in digest_fields:
            if field not in args:
                if field in ('job','bindings') and digest_field in args:raise ValueError(field+' path required')
                continue
            path=self.path(args[field]);actual=sha_file(path)
            if not automatic or digest_field in args:
                digest=args[digest_field]
                if not isinstance(digest,str)or not re.fullmatch('[0-9a-f]{64}',digest)or actual!=digest:
                    raise DiagnosticError('mcp.input_sha256_mismatch','Input digest mismatch: '+field,phase=operation,
                                          source=str(path),field=field,expected=digest,actual=actual)
            if str(path) in bound and bound[str(path)]!=actual:raise ValueError('Input changed during binding')
            args[field]=str(path);bound[str(path)]=actual;input_hashes[field]=actual
        if operation=='verify' and any(type(args.get(k,False)) is not bool for k in ('rebuild','portable','artifacts_only')):
            raise ValueError('Verification flags must be boolean')
        destination=self.path(args['output'],True)if 'output'in args else None
        if progress:await progress(0,3,'Inputs bound')
        # Only this request's private directory is removed on failure/cancellation.
        project, output_root = (None, None) if builtin else (self.project, self.output_root)
        with tempfile.TemporaryDirectory(prefix='qianxing-mcp-',dir=output_root)as temporary:
            scratch=Path(temporary);request=scratch/'request.json';result_path=scratch/'result.json'
            if destination:args['output']=str(scratch/'delivery')
            write_json(request,{'operation':operation,'arguments':args,'inputs':bound,
                               'project':str(project) if project else None,
                               'output_root':str(output_root) if output_root else None,'scratch':str(scratch)})
            process=None
            code=None
            with (scratch/'stdout.log').open('wb')as stdout,(scratch/'stderr.log').open('wb')as stderr:
                try:
                    from portable_trust import child_environment
                    process=await asyncio.create_subprocess_exec(sys.executable,'-X','utf8','-B',str(PLUGIN/'scripts/mcp_worker.py'),
                        str(request),str(result_path),cwd=project or PLUGIN,stdout=stdout,stderr=stderr,
                        env={**child_environment(),'PYTHONDONTWRITEBYTECODE':'1'},start_new_session=os.name!='nt')
                    if progress:await progress(1,3,'Core operation running')
                    code=await process.wait()
                finally:
                    if process is not None and (code is None or (os.name != 'nt' and code != 0)):
                        try:
                            await finish_worker(process)
                        except Exception as cleanup_error:
                            # The request's failure or cancellation remains the result.
                            import logging
                            logging.getLogger(__name__).warning('MCP worker cleanup: %s', cleanup_error)
            if code!=0:
                detail=(scratch/'stderr.log').read_text(encoding='utf-8',errors='replace')[-8000:] or f'MCP worker exited with status {code}'
                return {'schema':2,'operation':operation,'status':'failed','error':detail,'output':None}
            result=read_json(result_path)
            if operation == 'doctor':
                result['project_context'] = self.context
            for path,digest in bound.items():
                actual=sha_file(path)
                if actual!=digest:
                    raise DiagnosticError('mcp.input_changed','Input changed during operation',phase=operation,
                                          source=path,expected=digest,actual=actual)
            if progress:await progress(2,3,'Core result checked; ready to commit')
            await asyncio.sleep(0)
            status=result.get('status', 'failed'if result.get('passed')is False else'passed')
            if destination and status!='passed':
                response={'schema':2,'operation':operation,'status':status,'result':result,'output':None}
                if 'error' in result:response['error']=result['error']
                if 'diagnostics' in result:response['diagnostics']=result['diagnostics']
                return response
            output_hashes=None
            if destination:
                delivery=scratch/'delivery'
                if operation in ('native_plan','native_apply'):
                    manifest=delivery/'manifest.json'
                    output_hashes={**read_json(manifest)['files'],'manifest.json':sha_file(manifest)}
                self.path(str(destination),True)
                os.rename(delivery,destination)
                if operation=='produce' and 'output_directory' in result:result['output_directory']=str(destination)
            response={'schema':2,'operation':operation,'status':status,
                      'result':result,'output':str(destination)if destination else None}
            if automatic:response['inputs_sha256']=input_hashes
            if output_hashes is not None:response['outputs_sha256']=output_hashes
            return response


def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    for name in('serve','call'):
        command=sub.add_parser(name);command.add_argument('--project',default=os.environ.get('UGC_PROJECT_ROOT'));command.add_argument('--output-root',default=os.environ.get('UGC_OUTPUT_ROOT'))
        if name=='call':command.add_argument('request')
    args=parser.parse_args(argv)
    bridge=Bridge(args.project,args.output_root)
    if args.operation=='serve':
        from mcp_service import server
        server(bridge).run(transport='stdio');return 0
    request=read_json(args.request);schema(request,('schema','operation','arguments'),('operation','arguments'))
    result=asyncio.run(bridge.call(request['operation'],request['arguments']))
    print(json.dumps(result,ensure_ascii=False));return 1 if result['status']in('failed','not_checked')else 0
