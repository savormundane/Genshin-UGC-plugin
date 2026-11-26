"""Official MCP SDK stdio adapter for the shared fixed-operation bridge."""
from importlib.metadata import version
import asyncio
import json
from typing import Annotated, Any, Literal
from mcp import types
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from pydantic import StrictInt
from authoring_io import DiagnosticError
from miliastra.mcp.bridge import BUILTIN_OPERATIONS
from runtime_policy import REQUIREMENTS


def _preview_result(response, *, summary=None, error_on_failure=True):
    previews = response.get('result', {}).pop('_inline_previews', [])
    json_text = types.TextContent(type='text', text=json.dumps(response, ensure_ascii=False))
    content = [] if summary else [json_text]
    for preview in previews:
        content.extend([
            types.TextContent(type='text', text=preview['caption']),
            types.ImageContent(type='image', mime_type='image/png', data=preview['data']),
        ])
    if summary:
        content.extend([types.TextContent(type='text', text=summary), json_text])
    return types.CallToolResult(
        content=content, structured_content=response, is_error=error_on_failure and response['status'] == 'failed',
    )


def server(bridge):
    if version('mcp')!=REQUIREMENTS['mcp']:raise ValueError('MCP service requires pinned mcp=='+REQUIREMENTS['mcp'])
    app=MCPServer('Miliastra Wonderland')
    async def call(operation,ctx,**args):
        try:
            args = {k: v for k, v in args.items() if v is not None}
            roots = ()
            roots_error = None
            needs_workspace = operation == 'doctor' or operation not in BUILTIN_OPERATIONS or 'catalogue' in args
            if needs_workspace and not bridge.project and ctx.session.check_client_capability(
                    types.ClientCapabilities(roots=types.RootsCapability())):
                try:
                    listed = await asyncio.wait_for(ctx.session.list_roots(), 5)
                    roots = tuple(str(root.uri) for root in listed.roots)
                except (MCPError, TimeoutError) as exc:
                    unsupported = isinstance(exc, MCPError) and exc.code == types.METHOD_NOT_FOUND
                    if operation != 'doctor' and not unsupported:
                        raise DiagnosticError('mcp.roots_unavailable', 'Client workspace directories could not be read',
                                              phase=operation, detail=str(exc) or 'Roots request timed out') from exc
                    roots_error = str(exc) or 'Roots request timed out'
            response = await bridge.call(operation, args, ctx.report_progress, roots=roots)
            if operation == 'doctor' and roots_error and 'result' in response:
                response['result']['project_context']['roots_error'] = roots_error
            return response
        except DiagnosticError as exc:
            raise ToolError(json.dumps({'error':str(exc),'diagnostics':exc.diagnostics},ensure_ascii=False)) from exc
        except (ValueError,OSError) as exc:
            raise ToolError(str(exc)) from exc

    @app.tool(structured_output=True)
    async def api_lookup(symbol:str,ctx:Context)->dict[str,Any]:
        """Find a client Lua API by formal symbol, English fragment, or Chinese purpose. Return canonical symbols and source evidence."""
        return await call('api_lookup',ctx,symbol=symbol)
    @app.tool(structured_output=True)
    async def diagnose(spec:str,sha256:str,ctx:Context)->dict[str,Any]:
        """Run explicit read-only checks, preserving evidence layers and unknowns."""
        return await call('diagnose',ctx,spec=spec,sha256=sha256)
    @app.tool(structured_output=True)
    async def doctor(ctx:Context)->dict[str,Any]:
        """Read dependency availability without installing anything."""
        return await call('doctor',ctx)
    @app.tool(structured_output=True)
    async def capabilities(ctx:Context)->dict[str,Any]:
        """Report implemented capability coverage, with no invented acceptance."""
        return await call('capabilities',ctx)
    @app.tool(structured_output=True)
    async def docs_search(version:str,query:str,ctx:Context)->dict[str,Any]:
        """Search pinned platform documentation for an explicit version."""
        return await call('docs_search',ctx,version=version,query=query)
    @app.tool(structured_output=True)
    async def nodes_lookup(ctx:Context,query:str='',scope:str='all',limit:StrictInt=20)->dict[str,Any]:
        """Find bundled Graph Code definitions by name, invocation, or port. Use port_evidence for version-bound platform documentation."""
        return await call('nodes_lookup',ctx,query=query,scope=scope,limit=limit)
    @app.tool(structured_output=True)
    async def graph_check(input:str,ctx:Context,sha256:str|None=None,job:str|None=None,job_sha256:str|None=None,
                          bindings:str|None=None,bindings_sha256:str|None=None)->dict[str,Any]:
        """Validate a Graph Code file with optional production-job declarations. Returns diagnostics and input digests."""
        return await call('graph_check',ctx,input=input,sha256=sha256,job=job,job_sha256=job_sha256,
                          bindings=bindings,bindings_sha256=bindings_sha256)

    @app.tool(structured_output=True)
    async def graph_build(spec: str, output: str, ctx: Context, sha256: str | None = None) -> dict[str, Any]:
        """Compile Graph Code into independent GIA files.

        To add one to an existing GIL, pass its GIA path as the source of an
        append_graph operation in native_plan with allowed_top_level_fields=[10].
        """
        return await call('graph_build', ctx, spec=spec, output=output, sha256=sha256)
    @app.tool(structured_output=True)
    async def resources_lookup(version:str,ctx:Context,query:str='',mode:str='beyond',limit:int=20,
                               catalogue:str|None=None,catalogue_sha256:str|None=None,
                               resource_type:str|None=None)->dict[str,Any]:
        """Find model and template candidates or select a resource type such as sound or effect."""
        return await call('resources_lookup',ctx,version=version,query=query,mode=mode,limit=limit,
                          catalogue=catalogue,catalogue_sha256=catalogue_sha256,resource_type=resource_type)
    @app.tool(structured_output=True)
    async def native_inspect(input:str,ctx:Context,sha256:str|None=None)->dict[str,Any]:
        """Read native identities and return the file digest."""
        return await call('native_inspect',ctx,input=input,sha256=sha256)

    @app.tool(structured_output=True)
    async def scene_preview(
        input: str, output: str, ctx: Context, before: str | None = None,
        sha256: str | None = None, before_sha256: str | None = None,
    ) -> Annotated[types.CallToolResult, dict[str, Any]]:
        """Draw a scene draft or GIL layout, optionally comparing an earlier file at the same scale.

        Show the attached top and side views first, then the result and next step.
        """
        response = await call('scene_preview', ctx, input=input, output=output, before=before,
                              sha256=sha256, before_sha256=before_sha256)
        summary = None
        if response['status'] == 'passed':
            count = response['result']['objects']
            summary = f'布局预览已生成，报告记录了 {count} 个已定位对象。请核对点位和轮廓后再继续调整。'
        return _preview_result(response, summary=summary, error_on_failure=False)

    @app.tool(structured_output=True)
    async def scene_catalogue(input:str,sha256:str,version:str,mode:str,output:str,ctx:Context)->dict[str,Any]:
        """Capture readable static scene templates and their evidence from the selected GIL/GIA sample."""
        return await call('scene_catalogue',ctx,input=input,sha256=sha256,version=version,mode=mode,output=output)

    @app.tool(structured_output=True)
    async def scene_build(spec:str,sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Export a standalone static scene GIA using digest-bound layout and witnessed template IDs."""
        return await call('scene_build',ctx,spec=spec,sha256=sha256,output=output)

    @app.tool(structured_output=True)
    async def asset_preview(input:str,output:str,ctx:Context,sha256:str|None=None,
                            max_controls:StrictInt|None=None,step:StrictInt|None=None)->types.CallToolResult:
        """Compare PNG conversions. Show the original, recommended and cheaper viable previews when available, with counts and digests for asset_generate."""
        response = await call('asset_preview', ctx, input=input, output=output, sha256=sha256,
                              max_controls=max_controls, step=step)
        return _preview_result(response)

    @app.tool(structured_output=True)
    async def asset_generate(input: str, sha256: str, report: str, report_sha256: str,
                             candidate: str, output: str, ctx: Context) -> types.CallToolResult:
        """Generate the selected candidate into a new directory. Use asset_preview inputs_sha256.input and outputs_sha256['report.json'] for the digests."""
        response = await call('asset_generate', ctx, input=input, sha256=sha256, report=report,
                              report_sha256=report_sha256, candidate=candidate, output=output)
        return _preview_result(response)

    @app.tool(structured_output=True)
    async def asset_fit(input:str,spec:str,output:str,ctx:Context,sha256:str|None=None,
                        spec_sha256:str|None=None,resume:str|None=None,resume_sha256:str|None=None,
                        initial:str|None=None,initial_sha256:str|None=None,
                        steps:StrictInt|None=None)->types.CallToolResult:
        """Fit an image or ordered layer manifest within a control budget.

        With a GIL-bound mount, reuse result.mount.gil_binding.control_guid as
        the bind_client_lua target in native_plan. Use mounted.lua as source and
        catalog.json as fit_catalog, both in the returned output directory.
        For a software preview, pass beyond.json from that directory and its
        outputs_sha256 digest to simulate with preview=true.
        """
        response = await call('asset_fit',ctx,input=input,spec=spec,output=output,sha256=sha256,
                              spec_sha256=spec_sha256,resume=resume,resume_sha256=resume_sha256,
                              initial=initial,initial_sha256=initial_sha256,steps=steps)
        return _preview_result(response)

    @app.tool(structured_output=True)
    async def native_audit(input:str,ctx:Context,sha256:str|None=None)->dict[str,Any]:
        """Audit final native types and references without modifying input."""
        return await call('native_audit',ctx,input=input,sha256=sha256)
    @app.tool(structured_output=True)
    async def project_inspect(input:str,ctx:Context,sha256:str|None=None,
                              selector:dict[str,str|StrictInt]|None=None,transitive:bool|None=None,
                              scope:Literal['scene','gameplay']|None=None,summary:bool=False,
                              query:str|None=None,kind:str|None=None,limit:StrictInt|None=None)->dict[str,Any]:
        """Search by query for object keys or select a known object to read its references."""
        return await call('project_inspect',ctx,input=input,sha256=sha256,selector=selector,transitive=transitive,
                          scope=scope,summary=summary,query=query,kind=kind,limit=limit)
    @app.tool(structured_output=True)
    async def client_check(input:str,ctx:Context,sha256:str|None=None,contract:str|None=None,
                           contract_sha256:str|None=None,mapping:str|None=None)->dict[str,Any]:
        """Compile final Lua, optionally selecting one embedded mapping and checking an API contract."""
        return await call('client_check',ctx,input=input,sha256=sha256,contract=contract,
                          contract_sha256=contract_sha256,mapping=mapping)
    @app.tool(structured_output=True)
    async def produce(spec:str,sha256:str,output:str,ctx:Context,summary:bool=False)->dict[str,Any]:
        """Build a trusted project into a new output directory; cancellation prevents commit."""
        return await call('produce',ctx,spec=spec,sha256=sha256,output=output,summary=summary)
    @app.tool(structured_output=True)
    async def native_apply(input:str,sha256:str,plan:str,plan_sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Apply a reviewed native plan, preserving the original and existing outputs."""
        return await call('native_apply',ctx,input=input,sha256=sha256,plan=plan,plan_sha256=plan_sha256,output=output)
    @app.tool(structured_output=True)
    async def native_diff(input:str,other:str,ctx:Context,sha256:str|None=None,other_sha256:str|None=None,
                          allowed_top_level_fields:list[StrictInt]|None=None)->dict[str,Any]:
        """Compare two native files and optionally verify protected bytes outside the allowed fields."""
        return await call('native_diff',ctx,input=input,sha256=sha256,other=other,other_sha256=other_sha256,
                          allowed_top_level_fields=allowed_top_level_fields)
    @app.tool(structured_output=True)
    async def native_plan(input:str,sha256:str,output:str,ctx:Context,patch:dict[str,Any]|None=None,
                          spec:str|None=None,spec_sha256:str|None=None,summary:bool=False)->dict[str,Any]:
        """Plan a GIL edit using a schema 2 inline patch or a digest-bound spec.

        For Lua produced by a GIL-bound asset_fit, use allowed_top_level_fields
        [9, 50] and a bind_client_lua operation with control_guid, source,
        mapping (including .lua), and fit_catalog. Take control_guid from
        result.mount.gil_binding in the fit response.
        Review result.difference, then use outputs_sha256['plan.json'] for
        native_apply with the same input and sha256.
        """
        return await call('native_plan',ctx,input=input,sha256=sha256,output=output,patch=patch,spec=spec,spec_sha256=spec_sha256,summary=summary)
    @app.tool(structured_output=True)
    async def simulate(
        spec: str, sha256: str, output: str, ctx: Context, preview: bool = False,
    ) -> Annotated[types.CallToolResult, dict[str, Any]]:
        """Run a joint scenario, or with preview=true run a Beyond spec and attach its generated PNG.

        For a preview, show the image first, then the check results or failure reason and next step.
        A failed preview can include an image. Use structured status to judge the result.
        """
        response = await call('simulate', ctx, spec=spec, sha256=sha256, output=output, preview=preview)
        summary = None
        if preview and response['status'] == 'passed':
            checks = response['result']['checks']
            labels = {'passed': '通过', 'failed': '失败', 'not_checked': '未检查'}
            results = '，'.join(f"{name}{labels[checks[key]['status']]}" for key, name in (
                ('lua', 'Lua 执行'), ('assertions', '行为断言'), ('render_assertions', '绘制断言'),
            ))
            summary = f'{results}。请核对画面后再继续调整。'
        elif preview:
            reasons = '\n'.join(row['message'] for row in response.get('diagnostics', []))
            reasons = reasons or response.get('error', '未生成预览。')
            summary = f'预览失败。\n{reasons}\n处理报错后，用新的输出名称重试。'
        return _preview_result(response, summary=summary, error_on_failure=False)
    @app.tool(structured_output=True)
    async def experiment_run(spec:str,sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await call('experiment_run',ctx,spec=spec,sha256=sha256,output=output)
    @app.tool(structured_output=True)
    async def experiment_compare(input:str,sha256:str,other:str,other_sha256:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await call('experiment_compare',ctx,input=input,sha256=sha256,other=other,other_sha256=other_sha256)
    @app.tool(structured_output=True)
    async def logs_diagnose(spec:str,sha256:str,ctx:Context)->dict[str,Any]:
        """Diagnose structured JSONL or a supported editor debug-log export and correlate digest-bound artifacts."""
        return await call('logs_diagnose',ctx,spec=spec,sha256=sha256)
    @app.tool(structured_output=True)
    async def verify(input:str,sha256:str,ctx:Context,rebuild:bool=False,portable:bool=False,
                     trusted_inputs_sha256:str|None=None,artifacts_only:bool=False)->dict[str,Any]:
        """Verify artifacts, source digests, or a portable closure. Rebuild uses an explicitly trusted input digest."""
        return await call('verify',ctx,input=input,sha256=sha256,rebuild=rebuild,portable=portable,
                          trusted_inputs_sha256=trusted_inputs_sha256,artifacts_only=artifacts_only)
    return app
