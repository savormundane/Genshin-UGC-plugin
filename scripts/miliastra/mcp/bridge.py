"""Fixed operations shared by local MCP and CLI; no arbitrary command tool."""
from contextlib import nullcontext
from pathlib import Path
import argparse,asyncio,json,os,re,sys,tempfile,math
from authoring_io import DiagnosticError,PLUGIN,sha_file,schema,read_json,write_json,missing_input,require_new_output
from miliastra.mcp.workspace import data_directory, mounted_path, workspace as project_context

OPERATIONS={'doctor':(), 'capabilities':(), 'docs_search':('version','query'),'api_lookup':('symbol',),'nodes_lookup':(),'resources_lookup':('version',),'diagnose':('spec','sha256'),
            'native_inspect':('input',),'native_audit':('input',),
            'project_inspect':('input',),'client_check':('input',),'graph_check':('input',),'graph_build':('spec','output'),
            'native_diff':('input','other'), 'scene_preview':('input','output'), 'asset_preview':('input','output'),
            'scene_catalogue':('input','sha256','version','mode','output'),
            'scene_build':('spec','sha256','output'), 'asset_fit':('input','spec','output'),
            'asset_generate':('input','sha256','report','report_sha256','candidate','output'),
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
    'graph_build':('sha256',),
    'resources_lookup':('query','mode','limit','catalogue','catalogue_sha256','resource_type'),
    'scene_preview':('sha256','before','before_sha256'),
    'asset_preview':('sha256','max_controls','step'),
    'asset_fit':('sha256','spec_sha256','resume','resume_sha256','initial','initial_sha256','steps'),
}
OPTIONAL_FIELDS={**READ_FILE_OPERATIONS,'native_plan':('patch','spec','spec_sha256','summary'),'produce':('summary',),
                 'simulate':('preview',),
                 'nodes_lookup':('query','scope','limit'),'verify':('rebuild','portable','trusted_inputs_sha256','artifacts_only')}
BUILTIN_OPERATIONS = ('doctor', 'capabilities', 'docs_search', 'api_lookup', 'nodes_lookup', 'resources_lookup')
TIMEOUT_SETTINGS = {
    'ordinary': ('MILIASTRA_WONDERLAND_MCP_TIMEOUT_SECONDS', '120'),
    'build': ('MILIASTRA_WONDERLAND_MCP_BUILD_TIMEOUT_SECONDS', '900'),
}


def outside_allowed_roots(path, *, output):
    area = '输出根目录' if output else '工程目录或输出根目录'
    return DiagnosticError(
        'io.outside_allowed_roots',
        f'路径 {path} 不在已授权的{area}内。请从已授权目录选择文件或输出位置后重试。',
        source=str(path),
        detail='Path outside allowed project/output roots',
    )


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
        self.timeouts = {
            kind: float(os.environ.get(variable, default))
            for kind, (variable, default) in TIMEOUT_SETTINGS.items()
        }
        if any(not math.isfinite(value) or not 0 < value <= 3600 for value in self.timeouts.values()):
            raise ValueError('MCP timeouts must be finite seconds in (0, 3600]')
        self.project = project
        self.output_root = output_root

    def path(self, value, project, output_root, *, output=False, default_output=False):
        if not isinstance(value,str)or not value:raise ValueError('Nonempty path required')
        root = output_root if output else project
        original = Path(os.path.abspath(root / value))
        roots = [r for r in ([output_root] if output else [project, output_root]) if r is not None]
        resolved = mounted_path(original, roots, detail='Linked tool path refused')
        if resolved is None:
            raise outside_allowed_roots(original, output=output)
        if output:
            require_new_output(resolved)
            if not resolved.parent.is_dir() and not (default_output and resolved.parent == output_root):
                raise DiagnosticError(
                    'io.output_parent_missing',
                    f'输出位置的上一级目录 {resolved.parent} 不存在。请选用输出根目录内已有的父目录后重试。',
                    source=str(resolved.parent),
                    detail='Output parent must exist',
                )
        elif not resolved.is_file():raise missing_input(resolved)
        return resolved

    async def call(self,operation,arguments,progress=None,*,roots=()):
        build=operation in ('produce','native_apply','asset_fit','graph_build') or operation=='verify' and arguments.get('rebuild')
        kind = 'build' if build else 'ordinary'
        seconds = self.timeouts[kind]
        try:
            return await asyncio.wait_for(self._call(operation,arguments,progress,roots),seconds)
        except asyncio.TimeoutError:
            variable, _ = TIMEOUT_SETTINGS[kind]
            problem = DiagnosticError(
                'mcp.timeout',
                f'任务超过插件设定的 {seconds:g} 秒时限。请缩小处理范围，或提高 {variable} 后重试。',
                phase=operation, timeout_seconds=seconds, detail='MCP operation exceeded its total timeout',
            )
            return {'schema':2,'operation':operation,'status':'failed','error':str(problem),
                    'diagnostics':problem.diagnostics,'output':None}

    async def _call(self,operation,arguments,progress,roots):
        if operation not in OPERATIONS:raise ValueError('Unknown bridge operation')
        required=OPERATIONS[operation]
        schema(arguments,required+OPTIONAL_FIELDS.get(operation,()),required)
        args=dict(arguments);bound={};input_hashes={}
        automatic=operation in READ_FILE_OPERATIONS
        builtin = operation in BUILTIN_OPERATIONS and 'catalogue' not in args
        context = project_context(self.project, self.output_root, roots, args) if not builtin or operation == 'doctor' else {}
        project = Path(context['project_root']) if not builtin and context['project_root'] else None
        output_root = Path(context['output_root']) if not builtin and context['output_root'] else None
        project_required = not builtin and project is None
        if project_required or ('output' in args and output_root is None):
            if project_required:
                code = 'mcp.workspace_ambiguous' if context['status'] == 'ambiguous' else 'mcp.workspace_required'
                message, detail = context['message'], context.get('detail')
            else:
                code = 'mcp.output_required'
                message, detail = context['output_message'], context.get('output_detail')
            problem = context.get('directory_problem', {})
            fields = {'source': problem['source']} if problem else {}
            raise DiagnosticError(problem.get('code', code), message, phase=operation,
                                  context=context, detail=detail, **fields)
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
        if 'before_sha256' in args and 'before' not in args:raise ValueError('Before path required')
        if 'preview' in args and type(args['preview']) is not bool:raise ValueError('preview must be a boolean')
        if operation=='resources_lookup':
            limit=args.get('limit',20)
            if type(limit) is not int or not 1<=limit<=100:
                raise ValueError('Resource lookup limit must be from 1 to 100')
        digest_fields=(('catalogue','catalogue_sha256'),('input','sha256'),
                       ('spec','spec_sha256' if operation in ('native_plan','asset_fit') else 'sha256'),
                       ('resume','resume_sha256'),('initial','initial_sha256'),('other','other_sha256'),
                       ('plan','plan_sha256'),('report','report_sha256'),('contract','contract_sha256'),('job','job_sha256'),
                       ('bindings','bindings_sha256'),('before','before_sha256'))
        for field,digest_field in digest_fields:
            if field not in args:
                if field in ('job','bindings','resume','initial') and digest_field in args:raise ValueError(field+' path required')
                continue
            path=self.path(args[field],project,output_root);actual=sha_file(path)
            if not automatic or digest_field in args:
                digest=args[digest_field]
                if not isinstance(digest,str)or not re.fullmatch('[0-9a-f]{64}',digest)or actual!=digest:
                    raise DiagnosticError(
                        'mcp.input_sha256_mismatch',
                        f'输入 {field} 的文件与提供的 SHA-256 校验值不一致。请确认要用的文件版本，'
                        '如文件已修改，先重做依赖该文件的上一步，再用对应校验值重试。',
                        phase=operation, source=str(path), field=field, expected=digest, actual=actual,
                        detail='Input digest mismatch: '+field,
                    )
            if str(path) in bound and bound[str(path)]!=actual:
                raise DiagnosticError(
                    'mcp.input_changed', '读取输入时文件发生了变化。请结束正在编辑或同步的操作后重试。',
                    phase=operation, source=str(path), expected=bound[str(path)], actual=actual,
                    detail='Input changed during binding',
                )
            args[field]=str(path);bound[str(path)]=actual;input_hashes[field]=actual
        if operation == 'native_plan' and 'patch' in args:
            patch = args['patch']
            actual = input_hashes['input']
            if 'base_sha256' in patch and patch['base_sha256'] != actual:
                raise DiagnosticError(
                    'native.base_sha256_mismatch',
                    '补丁中的基底 SHA-256 校验值与当前 GIL 不一致。请针对当前 GIL 重新检查并准备修改计划。',
                    phase=operation, field='base_sha256', expected=actual, actual=patch['base_sha256'],
                    detail='Patch base_sha256 differs from the verified input',
                )
            args['patch'] = {**patch, 'base_sha256': actual}
        if operation=='verify' and any(type(args.get(k,False)) is not bool for k in ('rebuild','portable','artifacts_only')):
            raise ValueError('Verification flags must be boolean')
        destination = None
        if 'output' in args:
            default_output = context['output_source'] == 'plugin_data'
            destination = self.path(args['output'], project, output_root, output=True, default_output=default_output)
            if default_output:
                output_root.mkdir(parents=True, exist_ok=True)
        if progress:await progress(0,3,'Inputs bound')
        # Compiler files use private system temp. Delivery still stages on the output volume.
        compiler = tempfile.TemporaryDirectory(prefix='mw-') if operation == 'graph_build' else nullcontext()
        with (
            compiler as build_scratch,
            tempfile.TemporaryDirectory(
                prefix='qianxing-mcp-', dir=output_root if destination else None,
            ) as temporary,
        ):
            scratch=Path(temporary);request=scratch/'request.json';result_path=scratch/'result.json'
            if destination:args['output']=str(scratch/'delivery')
            write_json(request,{'operation':operation,'arguments':args,'inputs':bound,
                               'project':str(project) if project else None,
                               'output_root':str(output_root) if output_root else None,'scratch':str(scratch),
                               'build_scratch':build_scratch,
                               'destination':str(destination) if destination else None})
            process=None
            code=None
            with (scratch/'stdout.log').open('wb')as stdout,(scratch/'stderr.log').open('wb')as stderr:
                try:
                    from portable_trust import child_environment
                    env={**child_environment(),'PYTHONDONTWRITEBYTECODE':'1'}
                    if operation == 'produce' or (operation == 'simulate' and args.get('preview')):
                        env.update({
                            name: value for name, value in os.environ.items()
                            if name.upper() in ('HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY')
                            or name == 'MILIASTRA_WONDERLAND_BEYOND_NATIVE_ROOT'
                        })
                    if (data:=data_directory()) is not None:env['MILIASTRA_WONDERLAND_PLUGIN_DATA']=str(data)
                    process=await asyncio.create_subprocess_exec(sys.executable,'-X','utf8','-B',str(PLUGIN/'scripts/mcp_worker.py'),
                        str(request),str(result_path),cwd=project or PLUGIN,stdout=stdout,stderr=stderr,
                        env=env,start_new_session=os.name!='nt')
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
                result['project_context'] = context
            for path,digest in bound.items():
                actual=sha_file(path)
                if actual!=digest:
                    raise DiagnosticError(
                        'mcp.input_changed', '执行期间输入文件发生了变化。请确认当前版本并重新执行本次操作。',
                        phase=operation, source=path, expected=digest, actual=actual,
                        detail='Input changed during operation',
                    )
            if progress:await progress(2,3,'Core result checked; ready to commit')
            await asyncio.sleep(0)
            status=result.get('status', 'failed'if result.get('passed')is False else'passed')
            completed_experiment = operation == 'experiment_run' and result.get('kind') == 'experiment'
            if destination and status != 'passed' and not completed_experiment:
                response={'schema':2,'operation':operation,'status':status,'result':result,'output':None}
                if 'error' in result:response['error']=result['error']
                if 'diagnostics' in result:response['diagnostics']=result['diagnostics']
                if operation == 'simulate' and args.get('preview'):
                    delivery = scratch / 'delivery.diagnostics'
                    manifest = delivery / 'manifest.json'
                    if manifest.is_file():
                        diagnostics = destination.with_name(destination.name + '.diagnostics')
                        try:
                            self.path(str(diagnostics), project, output_root, output=True)
                            hashes = {**read_json(manifest)['files'], 'manifest.json': sha_file(manifest)}
                            os.rename(delivery, diagnostics)
                        except (ValueError, FileExistsError) as error:
                            response.setdefault('diagnostics', []).append({
                                'code': 'diagnostics_output_unavailable',
                                'message': f'无法保存预览诊断。请为预览指定新的输出路径。{error}',
                                'path': str(diagnostics),
                            })
                        else:
                            response['diagnostics_output'] = str(diagnostics)
                            response['diagnostics_sha256'] = hashes
                return response
            output_hashes=None
            if destination:
                delivery=scratch/'delivery'
                manifest = delivery / 'manifest.json'
                if operation == 'produce':
                    # Portable deliveries can list thousands of files. Return the two
                    # entry points for follow-up verification without copying the list.
                    output_hashes = {'production-report.json': sha_file(delivery / 'production-report.json')}
                    if manifest.is_file():
                        output_hashes['manifest.json'] = sha_file(manifest)
                elif operation == 'asset_preview':
                    output_hashes = {
                        'report.json': sha_file(delivery / 'report.json'),
                        'manifest.json': sha_file(manifest),
                    }
                else:
                    field = 'files_sha256' if operation == 'asset_generate' else 'files'
                    output_hashes = {**read_json(manifest)[field], 'manifest.json': sha_file(manifest)}
                self.path(str(destination),project,output_root,output=True)
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
        command=sub.add_parser(name);command.add_argument('--project',default=os.environ.get('MILIASTRA_WONDERLAND_PROJECT_ROOT'));command.add_argument('--output-root',default=os.environ.get('MILIASTRA_WONDERLAND_OUTPUT_ROOT'))
        if name=='call':command.add_argument('request')
    args=parser.parse_args(argv)
    bridge=Bridge(args.project,args.output_root)
    if args.operation=='serve':
        from miliastra.mcp.service import server
        server(bridge).run(transport='stdio');return 0
    request=read_json(args.request);schema(request,('schema','operation','arguments'),('operation','arguments'))
    result=asyncio.run(bridge.call(request['operation'],request['arguments']))
    result.get('result', {}).pop('_inline_previews', None)
    print(json.dumps(result,ensure_ascii=False));return 1 if result['status']in('failed','not_checked')else 0
