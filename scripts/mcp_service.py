"""Official MCP SDK stdio adapter for the shared fixed-operation bridge."""
from importlib.metadata import version
from typing import Any
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import StrictInt


def server(bridge):
    if version('mcp')!='2.3.0':raise ValueError('MCP service requires pinned mcp==2.3.0')
    app=MCPServer('Genshin-UGC')
    async def call(operation,ctx,**args):
        try:
            return await bridge.call(operation,{k:v for k,v in args.items() if v is not None},ctx.report_progress)
        except (ValueError,OSError) as exc:
            raise ToolError(str(exc)) from exc

    @app.tool(structured_output=True)
    async def api_lookup(symbol:str,ctx:Context)->dict[str,Any]:
        """Query a source-bound API signature and its declared/derived basis."""
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
        """Find Graph Code nodes by name, invocation, or port metadata in all, client, or server scope."""
        return await call('nodes_lookup',ctx,query=query,scope=scope,limit=limit)
    @app.tool(structured_output=True)
    async def resources_lookup(version:str,ctx:Context,query:str='',mode:str='beyond',limit:int=20,
                               catalogue:str|None=None,catalogue_sha256:str|None=None)->dict[str,Any]:
        """Find native model candidates or template IDs witnessed by a project catalogue."""
        return await call('resources_lookup',ctx,version=version,query=query,mode=mode,limit=limit,
                          catalogue=catalogue,catalogue_sha256=catalogue_sha256)
    @app.tool(structured_output=True)
    async def native_inspect(input:str,ctx:Context,sha256:str|None=None)->dict[str,Any]:
        """Read native identities and return the file digest."""
        return await call('native_inspect',ctx,input=input,sha256=sha256)
    @app.tool(structured_output=True)
    async def native_audit(input:str,ctx:Context,sha256:str|None=None)->dict[str,Any]:
        """Audit final native types and references without modifying input."""
        return await call('native_audit',ctx,input=input,sha256=sha256)
    @app.tool(structured_output=True)
    async def project_inspect(input:str,ctx:Context,sha256:str|None=None,
                              selector:dict[str,str|StrictInt]|None=None,transitive:bool|None=None)->dict[str,Any]:
        """Read native objects and script mappings, or select one object and its known dependencies and consumers."""
        return await call('project_inspect',ctx,input=input,sha256=sha256,selector=selector,transitive=transitive)
    @app.tool(structured_output=True)
    async def client_check(input:str,ctx:Context,sha256:str|None=None,contract:str|None=None,
                           contract_sha256:str|None=None,mapping:str|None=None)->dict[str,Any]:
        """Compile final Lua, optionally selecting one embedded mapping and checking an API contract."""
        return await call('client_check',ctx,input=input,sha256=sha256,contract=contract,
                          contract_sha256=contract_sha256,mapping=mapping)
    @app.tool(structured_output=True)
    async def produce(spec:str,sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Build a trusted project into a new output directory; cancellation prevents commit."""
        return await call('produce',ctx,spec=spec,sha256=sha256,output=output)
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
                          spec:str|None=None,spec_sha256:str|None=None)->dict[str,Any]:
        """Plan a GIL edit from an inline patch or a digest-bound spec. Review result.difference and use outputs_sha256 for native_apply."""
        return await call('native_plan',ctx,input=input,sha256=sha256,output=output,patch=patch,spec=spec,spec_sha256=spec_sha256)
    @app.tool(structured_output=True)
    async def simulate(spec:str,sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await call('simulate',ctx,spec=spec,sha256=sha256,output=output)
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
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await call('logs_diagnose',ctx,spec=spec,sha256=sha256)
    @app.tool(structured_output=True)
    async def verify(input:str,sha256:str,rebuild:bool,portable:bool,ctx:Context,trusted_inputs_sha256:str|None=None)->dict[str,Any]:
        """Static portable verification never executes package code. Rebuild requires explicit trusted project-input approval."""
        return await call('verify',ctx,input=input,sha256=sha256,rebuild=rebuild,portable=portable,
                          trusted_inputs_sha256=trusted_inputs_sha256)
    return app
