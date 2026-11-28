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
from pydantic import Field, StrictInt
from authoring_io import DiagnosticError, PLUGIN, read_json
from miliastra.mcp.bridge import BUILTIN_OPERATIONS
from runtime_policy import REQUIREMENTS


READ_ONLY = types.ToolAnnotations(readOnlyHint=True, openWorldHint=False)
NEW_OUTPUT = types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)
MAY_DOWNLOAD = types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)

InputChecksum = Annotated[str, Field(description='input 文件的 SHA-256 校验值，用 64 个小写十六进制字符。')]
OptionalInputChecksum = Annotated[
    str | None, Field(description='input 文件的 SHA-256 校验值。省略时由工具计算。')
]
SpecChecksum = Annotated[str, Field(description='spec 文件的 SHA-256 校验值，用 64 个小写十六进制字符。')]
OptionalSpecChecksum = Annotated[str | None, Field(description='spec 文件的 SHA-256 校验值。')]
TargetVersion = Annotated[str, Field(description='要查阅或面向的千星奇域版本。')]
TargetMode = Annotated[str, Field(description='目标模式，可用 classic 或 beyond。')]
OutputDirectory = Annotated[str, Field(description='已授权输出目录下的新目录名或绝对路径。')]


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
    app = MCPServer('Miliastra Wonderland', version=read_json(PLUGIN / 'plugin.json')['version'])
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
                        raise DiagnosticError('mcp.roots_unavailable', '无法读取客户端的工程目录。请重新打开并授权实际工程目录后重试。',
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

    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def api_lookup(
        symbol: Annotated[str, Field(description='API 正式名称、英文片段或中文用途。')],
        ctx: Context,
    ) -> dict[str, Any]:
        """查客户端 Lua API 的正式名称、签名和来源依据。"""
        return await call('api_lookup',ctx,symbol=symbol)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def diagnose(
        spec: Annotated[str, Field(description='列出待查文件和检查项的诊断配置 JSON 路径。')],
        sha256: SpecChecksum,
        ctx: Context,
    ) -> dict[str, Any]:
        """按诊断配置检查工程文件，报告定位依据与各项检查结果。"""
        return await call('diagnose',ctx,spec=spec,sha256=sha256)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def doctor(ctx: Context) -> dict[str, Any]:
        """检查插件依赖、加载版本和已绑定的工程目录。"""
        return await call('doctor',ctx)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def capabilities(ctx: Context) -> dict[str, Any]:
        """查看插件版本、任务分组和可用工具。详细验证报告见返回的 CLI 命令。"""
        return await call('capabilities',ctx)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def docs_search(
        version: TargetVersion,
        query: Annotated[str, Field(description='中文提问、术语或关键词。')],
        ctx: Context,
    ) -> dict[str, Any]:
        """查询随包规则要点及官方链接。结果标为 index_only 时需查原文，无法访问时说明未查到规则依据。"""
        return await call('docs_search',ctx,version=version,query=query)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def nodes_lookup(
        ctx: Context,
        query: Annotated[str, Field(description='节点名称、调用名称或端口关键词。留空列出节点。')] = '',
        scope: Annotated[str, Field(description='节点作用域，all 为全部，client 为客户端，server 为服务端。')] = 'all',
        limit: Annotated[StrictInt, Field(description='最多返回的节点数，范围 1 到 100。')] = 20,
    ) -> dict[str, Any]:
        """查节点签名和端口。需要确认平台版本时，读取结果中该节点的 port_evidence。"""
        return await call('nodes_lookup',ctx,query=query,scope=scope,limit=limit)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def graph_check(
        input: Annotated[str, Field(description='待检查的 Graph Code Python 源文件路径。')],
        ctx: Context,
        sha256: OptionalInputChecksum = None,
        job: Annotated[str | None, Field(description='用于读取工程声明的制作任务 JSON 路径。')] = None,
        job_sha256: Annotated[str | None, Field(description='job 文件的 SHA-256 校验值。')] = None,
        bindings: Annotated[str | None, Field(description='具名对象绑定配置 JSON 路径。')] = None,
        bindings_sha256: Annotated[str | None, Field(description='bindings 文件的 SHA-256 校验值。')] = None,
    ) -> dict[str, Any]:
        """检查 Graph Code 源文件及工程声明，返回诊断和实际读取文件的校验值。"""
        return await call('graph_check',ctx,input=input,sha256=sha256,job=job,job_sha256=job_sha256,
                          bindings=bindings,bindings_sha256=bindings_sha256)

    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def graph_build(
        spec: Annotated[str, Field(description='schema 1 构建配置 JSON 路径。若填写 formats，使用 ["gia"]。')],
        output: OutputDirectory,
        ctx: Context,
        sha256: Annotated[str | None, Field(description='spec 文件的 SHA-256 校验值。省略时由工具计算。')] = None,
    ) -> dict[str, Any]:
        """编译独立 GIA，保存到新的输出目录。

        使用可信的工程源文件和静态信号声明。要加入已有 GIL，先将生成的 GIA
        作为 native_plan 中 append_graph 操作的 source，并允许顶层字段 10。
        """
        return await call('graph_build', ctx, spec=spec, output=output, sha256=sha256)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def resources_lookup(
        version: TargetVersion,
        ctx: Context,
        query: Annotated[str, Field(description='资源名称、编号或分类关键词。')] = '',
        mode: TargetMode = 'beyond',
        limit: Annotated[int, Field(description='最多返回的资源数，范围 1 到 100。')] = 20,
        catalogue: Annotated[str | None, Field(description='补充查询的本地资源目录 JSON 路径。')] = None,
        catalogue_sha256: Annotated[str | None, Field(description='catalogue 文件的 SHA-256 校验值。')] = None,
        resource_type: Annotated[str | None, Field(description='资源类型，例如 model、sound 或 effect。')] = None,
    ) -> dict[str, Any]:
        """按目标版本和模式查询模型、模板、音效或特效。可读取额外的本地资源目录。"""
        return await call('resources_lookup',ctx,version=version,query=query,mode=mode,limit=limit,
                          catalogue=catalogue,catalogue_sha256=catalogue_sha256,resource_type=resource_type)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def native_inspect(
        input: Annotated[str, Field(description='待查看的 GIL 或 GIA 文件路径。')],
        ctx: Context,
        sha256: OptionalInputChecksum = None,
    ) -> dict[str, Any]:
        """读取原生文件中的对象和声明，并返回文件校验值。"""
        return await call('native_inspect',ctx,input=input,sha256=sha256)

    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def scene_preview(
        input: Annotated[str, Field(description='场景草案 JSON 或当前布局 GIL 文件路径。')],
        output: OutputDirectory,
        ctx: Context,
        before: Annotated[str | None, Field(description='可选的旧版布局 GIL 路径，用于对比。')] = None,
        sha256: OptionalInputChecksum = None,
        before_sha256: Annotated[str | None, Field(description='before 文件的 SHA-256 校验值。')] = None,
    ) -> Annotated[types.CallToolResult, dict[str, Any]]:
        """将场景草案或 GIL 布局画成俯视图和侧视图，另存图片和报告。可按同一比例对比旧版布局。

        先展示附带的图，再说明检查结果和下一步。
        """
        response = await call('scene_preview', ctx, input=input, output=output, before=before,
                              sha256=sha256, before_sha256=before_sha256)
        summary = None
        if response['status'] == 'passed':
            count = response['result']['objects']
            summary = f'布局预览已生成，报告记录了 {count} 个已定位对象。请核对点位和轮廓后再继续调整。'
        return _preview_result(response, summary=summary, error_on_failure=False)

    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def scene_catalogue(
        input: Annotated[str, Field(description='用于见证布景模板的 GIL 或 GIA 样本路径。')],
        sha256: InputChecksum,
        version: TargetVersion,
        mode: TargetMode,
        output: OutputDirectory,
        ctx: Context,
    ) -> dict[str, Any]:
        """从选定的原生样本提取静态布景模板，保存模板目录和来源依据。"""
        return await call('scene_catalogue',ctx,input=input,sha256=sha256,version=version,mode=mode,output=output)

    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def scene_build(
        spec: Annotated[str, Field(description='绑定布局与已见证模板 ID 的布景配置 JSON 路径。')],
        sha256: SpecChecksum,
        output: OutputDirectory,
        ctx: Context,
    ) -> dict[str, Any]:
        """按照布景配置导出独立静态 GIA。"""
        return await call('scene_build',ctx,spec=spec,sha256=sha256,output=output)

    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def asset_preview(
        input: Annotated[str, Field(description='待试算的 PNG 图片路径。')],
        output: OutputDirectory,
        ctx: Context,
        sha256: OptionalInputChecksum = None,
        max_controls: Annotated[StrictInt | None, Field(description='可接受的最大控件数。')] = None,
        step: Annotated[StrictInt | None, Field(description='参考采样步长，默认为 1，即原尺寸。')] = None,
    ) -> types.CallToolResult:
        """试算 PNG 转图元并保存候选预览和报告。展示参考图、可用的首选及省控件候选和实际控件数。"""
        response = await call('asset_preview', ctx, input=input, output=output, sha256=sha256,
                              max_controls=max_controls, step=step)
        return _preview_result(response)

    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def asset_generate(
        input: Annotated[str, Field(description='与试算报告绑定的原 PNG 路径。')],
        sha256: Annotated[str, Field(description='asset_preview 返回的 inputs_sha256.input。')],
        report: Annotated[str, Field(description='试算输出中的 report.json 路径。')],
        report_sha256: Annotated[str, Field(description='asset_preview 返回的 outputs_sha256["report.json"]。')],
        candidate: Annotated[str, Field(description='试算报告中的候选名称。')],
        output: OutputDirectory,
        ctx: Context,
    ) -> types.CallToolResult:
        """生成试算报告中已选定的候选素材，保存图元数据和参考图。"""
        response = await call('asset_generate', ctx, input=input, sha256=sha256, report=report,
                              report_sha256=report_sha256, candidate=candidate, output=output)
        return _preview_result(response)

    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def asset_fit(
        input: Annotated[str, Field(description='源图片路径或列出分层顺序的清单 JSON 路径。')],
        spec: Annotated[str, Field(description='设定拟合参数、控件预算和可选挂载目标的 JSON 路径。')],
        output: OutputDirectory,
        ctx: Context,
        sha256: OptionalInputChecksum = None,
        spec_sha256: OptionalSpecChecksum = None,
        resume: Annotated[str | None, Field(description='从此前拟合继续计算所用的检查点路径。')] = None,
        resume_sha256: Annotated[str | None, Field(description='resume 文件的 SHA-256 校验值。')] = None,
        initial: Annotated[str | None, Field(description='只复用图元作为初始形状的检查点路径。与 resume 二选一。')] = None,
        initial_sha256: Annotated[str | None, Field(description='initial 文件的 SHA-256 校验值。')] = None,
        steps: Annotated[StrictInt | None, Field(description='本次拟合最多执行的步数。')] = None,
    ) -> types.CallToolResult:
        """按控件预算拟合图片或分层素材，保存预览和报告。

        对于绑定 GIL 的挂载，用 result.mount.gil_binding.control_guid 定位 native_plan
        的 bind_client_lua 目标。source 和 fit_catalog 使用输出目录内的 mounted.lua 和
        catalog.json。需要软件预览时，把同目录的 beyond.json 和对应校验值传给
        simulate，并设 preview=true。
        """
        response = await call('asset_fit',ctx,input=input,spec=spec,output=output,sha256=sha256,
                              spec_sha256=spec_sha256,resume=resume,resume_sha256=resume_sha256,
                              initial=initial,initial_sha256=initial_sha256,steps=steps)
        return _preview_result(response)

    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def native_audit(
        input: Annotated[str, Field(description='待审计的原生文件路径。')],
        ctx: Context,
        sha256: OptionalInputChecksum = None,
    ) -> dict[str, Any]:
        """只读审计原生文件中的类型和引用，返回检查结果。"""
        return await call('native_audit',ctx,input=input,sha256=sha256)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def project_inspect(
        input: Annotated[str, Field(description='待查看的 GIL、GIA 或工程索引配置 JSON 路径。')],
        ctx: Context,
        sha256: OptionalInputChecksum = None,
        selector: Annotated[dict[str, str | StrictInt] | None, Field(description='定位已知对象的选择器。与 query 二选一。')] = None,
        transitive: Annotated[bool | None, Field(description='给出 selector 时，可包含间接引用。')] = None,
        scope: Annotated[Literal['scene', 'gameplay'] | None, Field(description='GIL 或 GIA 的读取范围。scene 为场景，gameplay 为玩法。')] = None,
        summary: Annotated[bool, Field(description='返回工程概览。与 query 互斥。')] = False,
        query: Annotated[str | None, Field(description='用对象名或关键词查找工程对象。')] = None,
        kind: Annotated[str | None, Field(description='给出 query 时，按对象类型筛选。')] = None,
        limit: Annotated[StrictInt | None, Field(description='给出 query 时，限制返回的对象数。')] = None,
    ) -> dict[str, Any]:
        """查看工程概览，或按关键词找对象，再从已知对象读取引用。"""
        return await call('project_inspect',ctx,input=input,sha256=sha256,selector=selector,transitive=transitive,
                          scope=scope,summary=summary,query=query,kind=kind,limit=limit)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def client_check(
        input: Annotated[str, Field(description='待检查的 Lua 源文件或包含 Lua 的 GIL 路径。')],
        ctx: Context,
        sha256: OptionalInputChecksum = None,
        contract: Annotated[str | None, Field(description='可选的客户端 API 检查约定 JSON 路径。')] = None,
        contract_sha256: Annotated[str | None, Field(description='contract 文件的 SHA-256 校验值。')] = None,
        mapping: Annotated[str | None, Field(description='GIL 内要检查的 Lua 映射名称。')] = None,
    ) -> dict[str, Any]:
        """检查客户端 Lua 语法及 API 用法，可选定一条 GIL 内的脚本映射。"""
        return await call('client_check',ctx,input=input,sha256=sha256,contract=contract,
                          contract_sha256=contract_sha256,mapping=mapping)
    @app.tool(structured_output=True, annotations=MAY_DOWNLOAD)
    async def produce(
        spec: Annotated[str, Field(description='描述制作步骤及输入文件的任务配置 JSON 路径。')],
        sha256: SpecChecksum,
        output: OutputDirectory,
        ctx: Context,
        summary: Annotated[bool, Field(description='只返回制作概览，详细报告仍保存到输出目录。')] = False,
    ) -> dict[str, Any]:
        """按可信的任务配置制作产物并另存。提交前取消会停止交付。

        信号和结构体使用静态声明。任务包含 Beyond 预览时，可能下载并缓存渲染依赖。
        """
        return await call('produce',ctx,spec=spec,sha256=sha256,output=output,summary=summary)
    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def native_apply(
        input: Annotated[str, Field(description='审阅修改计划时使用的基底 GIL 路径。')],
        sha256: InputChecksum,
        plan: Annotated[str, Field(description='已审阅的 plan.json 路径。')],
        plan_sha256: Annotated[str, Field(description='已审阅的 plan.json 的 SHA-256 校验值。')],
        output: OutputDirectory,
        ctx: Context,
    ) -> dict[str, Any]:
        """校验基底和计划文件后，应用已审阅的计划并另存 GIL。"""
        return await call('native_apply',ctx,input=input,sha256=sha256,plan=plan,plan_sha256=plan_sha256,output=output)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def native_diff(
        input: Annotated[str, Field(description='作为基准比较的原生文件路径。')],
        other: Annotated[str, Field(description='与基准比较的另一份原生文件路径。')],
        ctx: Context,
        sha256: OptionalInputChecksum = None,
        other_sha256: Annotated[str | None, Field(description='other 文件的 SHA-256 校验值。')] = None,
        allowed_top_level_fields: Annotated[list[StrictInt] | None, Field(description='可变化的顶层字段编号。其余字节纳入保护校验。')] = None,
    ) -> dict[str, Any]:
        """比较两份原生文件，可检查允许范围外的字节是否原样保留。"""
        return await call('native_diff',ctx,input=input,sha256=sha256,other=other,other_sha256=other_sha256,
                          allowed_top_level_fields=allowed_top_level_fields)
    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def native_plan(
        input: Annotated[str, Field(description='用于生成修改计划的基底 GIL 路径。')],
        sha256: InputChecksum,
        output: OutputDirectory,
        ctx: Context,
        patch: Annotated[dict[str, Any] | None, Field(description='直接提供的 schema 2 修改配置。与 spec 二选一。')] = None,
        spec: Annotated[str | None, Field(description='schema 2 修改配置 JSON 路径，须同时提供 spec_sha256。')] = None,
        spec_sha256: OptionalSpecChecksum = None,
        summary: Annotated[bool, Field(description='返回计划概览，完整计划仍保存到输出目录。')] = False,
    ) -> dict[str, Any]:
        """生成 GIL 修改计划并另存。审阅差异后，再把 plan.json 的校验值和同一份基底传给 native_apply。

        接入绑定 GIL 的 asset_fit 生成的 Lua 时，允许顶层字段 [9, 50]。为 bind_client_lua
        提供 control_guid、source、含 .lua 的 mapping 及 fit_catalog。control_guid 取自
        result.mount.gil_binding。审阅 result.difference 后，从 outputs_sha256["plan.json"]
        读取校验值。
        """
        return await call('native_plan',ctx,input=input,sha256=sha256,output=output,patch=patch,spec=spec,spec_sha256=spec_sha256,summary=summary)
    @app.tool(structured_output=True, annotations=MAY_DOWNLOAD)
    async def simulate(
        spec: Annotated[str, Field(description='联合模拟配置 JSON 路径。preview=true 时使用 Beyond 预览配置。')],
        sha256: SpecChecksum,
        output: OutputDirectory,
        ctx: Context,
        preview: Annotated[bool, Field(description='使用 Beyond 生成软件预览并返回图片。')] = False,
    ) -> Annotated[types.CallToolResult, dict[str, Any]]:
        """运行联合模拟并保存报告。preview=true 时生成 Beyond 软件预览，可能下载并缓存渲染依赖。

        先展示附带的图，再说明检查结果或失败原因和下一步。失败时也可能附图，是否通过看 status。
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
    @app.tool(structured_output=True, annotations=NEW_OUTPUT)
    async def experiment_run(
        spec: Annotated[str, Field(description='指定 Lua 入口、种子、策略、观测指标的实验配置 JSON 路径。')],
        sha256: SpecChecksum,
        output: OutputDirectory,
        ctx: Context,
    ) -> dict[str, Any]:
        """按种子分组和策略运行离线 Lua 模拟，保存 observations.json 并返回其校验值。用例失败后仍可用报告配对比较。"""
        return await call('experiment_run',ctx,spec=spec,sha256=sha256,output=output)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def experiment_compare(
        input: Annotated[str, Field(description='基准实验生成的 observations.json 路径。')],
        sha256: InputChecksum,
        other: Annotated[str, Field(description='用于配对比较的另一份 observations.json 路径。')],
        other_sha256: Annotated[str, Field(description='other 文件的 SHA-256 校验值。')],
        ctx: Context,
    ) -> dict[str, Any]:
        """读取两份已有观察报告，用相同种子、策略和指标配对比较，返回数值差异。"""
        return await call('experiment_compare',ctx,input=input,sha256=sha256,other=other,other_sha256=other_sha256)
    @app.tool(structured_output=True, annotations=READ_ONLY)
    async def logs_diagnose(
        spec: Annotated[str, Field(description='指定结构化 JSONL 或编辑器调试日志及关联产物的配置 JSON 路径。')],
        sha256: SpecChecksum,
        ctx: Context,
    ) -> dict[str, Any]:
        """分析支持的日志文件，结合产物校验值定位问题。"""
        return await call('logs_diagnose',ctx,spec=spec,sha256=sha256)
    @app.tool(structured_output=True, annotations=MAY_DOWNLOAD)
    async def verify(
        input: Annotated[str, Field(description='交付目录内的 manifest.json 路径。')],
        sha256: InputChecksum,
        ctx: Context,
        rebuild: Annotated[bool, Field(description='用可信的可移植输入在临时目录重建，并对比产物。')] = False,
        portable: Annotated[bool, Field(description='检查交付内一并保存的可移植输入。重建时设为 true。')] = False,
        trusted_inputs_sha256: Annotated[str | None, Field(description='重建时显式确认的可信输入集 SHA-256 校验值。')] = None,
        artifacts_only: Annotated[bool, Field(description='仅校验产物。与 portable、rebuild 及 trusted_inputs_sha256 互斥。')] = False,
    ) -> dict[str, Any]:
        """校验产物与来源。可从已确认可信的输入重建，重建可能下载并缓存渲染依赖。"""
        return await call('verify',ctx,input=input,sha256=sha256,rebuild=rebuild,portable=portable,
                          trusted_inputs_sha256=trusted_inputs_sha256,artifacts_only=artifacts_only)
    return app
