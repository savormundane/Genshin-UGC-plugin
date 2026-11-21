"""Official MCP SDK stdio adapter for the shared fixed-operation bridge."""
from importlib.metadata import version
from typing import Any
from mcp.server import MCPServer
from mcp.server.mcpserver import Context


def server(bridge):
    if version('mcp')!='2.3.0':raise ValueError('MCP service requires pinned mcp==2.3.0')
    app=MCPServer('Genshin-UGC')
    async def read(operation,ctx,**args):
        return await bridge.call(operation,{k:v for k,v in args.items() if v is not None},ctx.report_progress)

    @app.tool(structured_output=True)
    async def api_lookup(symbol:str,ctx:Context)->dict[str,Any]:
        """Query a source-bound API signature and its declared/derived basis."""
        return await bridge.call('api_lookup',{'symbol':symbol},ctx.report_progress)
    @app.tool(structured_output=True)
    async def diagnose(spec:str,sha256:str,ctx:Context)->dict[str,Any]:
        """Run explicit read-only checks, preserving evidence layers and unknowns."""
        return await bridge.call('diagnose',{'spec':spec,'sha256':sha256},ctx.report_progress)
    @app.tool(structured_output=True)
    async def doctor(ctx:Context)->dict[str,Any]:
        """Read dependency availability without installing anything."""
        return await bridge.call('doctor',{},ctx.report_progress)
    @app.tool(structured_output=True)
    async def capabilities(ctx:Context)->dict[str,Any]:
        """Report implemented capability coverage, with no invented acceptance."""
        return await bridge.call('capabilities',{},ctx.report_progress)
    @app.tool(structured_output=True)
    async def docs_search(version:str,query:str,ctx:Context)->dict[str,Any]:
        """Search pinned platform documentation for an explicit version."""
        return await bridge.call('docs_search',{'version':version,'query':query},ctx.report_progress)
    @app.tool(structured_output=True)
    async def nodes_lookup(ctx:Context,query:str='',scope:str='all',limit:int=20)->dict[str,Any]:
        """Find Graph Code nodes by name, invocation, or port metadata in all, client, or server scope."""
        return await bridge.call('nodes_lookup',{'query':query,'scope':scope,'limit':limit},ctx.report_progress)
    @app.tool(structured_output=True)
    async def native_inspect(input:str,ctx:Context,sha256:str|None=None)->dict[str,Any]:
        """Read native identities and return the file digest."""
        return await read('native_inspect',ctx,input=input,sha256=sha256)
    @app.tool(structured_output=True)
    async def native_audit(input:str,ctx:Context,sha256:str|None=None)->dict[str,Any]:
        """Audit final native types and references without modifying input."""
        return await read('native_audit',ctx,input=input,sha256=sha256)
    @app.tool(structured_output=True)
    async def project_inspect(input:str,ctx:Context,sha256:str|None=None)->dict[str,Any]:
        """Index native objects and known references; report coverage limits."""
        return await read('project_inspect',ctx,input=input,sha256=sha256)
    @app.tool(structured_output=True)
    async def client_check(input:str,ctx:Context,sha256:str|None=None,contract:str|None=None,
                           contract_sha256:str|None=None,mapping:str|None=None)->dict[str,Any]:
        """Compile final Lua, optionally selecting one embedded mapping and checking an API contract."""
        return await read('client_check',ctx,input=input,sha256=sha256,contract=contract,
                          contract_sha256=contract_sha256,mapping=mapping)
    @app.tool(structured_output=True)
    async def produce(spec:str,sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Build a trusted project into a new output directory; cancellation prevents commit."""
        return await bridge.call('produce',{'spec':spec,'sha256':sha256,'output':output},ctx.report_progress)
    @app.tool(structured_output=True)
    async def native_apply(input:str,sha256:str,plan:str,plan_sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Apply a reviewed native plan, preserving the original and existing outputs."""
        return await bridge.call('native_apply',{'input':input,'sha256':sha256,'plan':plan,'plan_sha256':plan_sha256,'output':output},ctx.report_progress)
    @app.tool(structured_output=True)
    async def native_diff(input:str,other:str,ctx:Context,sha256:str|None=None,other_sha256:str|None=None)->dict[str,Any]:
        """Compare two native files and return their digests without writing an output."""
        return await read('native_diff',ctx,input=input,sha256=sha256,other=other,other_sha256=other_sha256)
    @app.tool(structured_output=True)
    async def native_plan(input:str,sha256:str,spec:str,spec_sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await bridge.call('native_plan',{'input':input,'sha256':sha256,'spec':spec,'spec_sha256':spec_sha256,'output':output},ctx.report_progress)
    @app.tool(structured_output=True)
    async def simulate(spec:str,sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await bridge.call('simulate',{'spec':spec,'sha256':sha256,'output':output},ctx.report_progress)
    @app.tool(structured_output=True)
    async def experiment_run(spec:str,sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await bridge.call('experiment_run',{'spec':spec,'sha256':sha256,'output':output},ctx.report_progress)
    @app.tool(structured_output=True)
    async def experiment_compare(input:str,sha256:str,other:str,other_sha256:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await bridge.call('experiment_compare',{'input':input,'sha256':sha256,'other':other,'other_sha256':other_sha256},ctx.report_progress)
    @app.tool(structured_output=True)
    async def logs_diagnose(spec:str,sha256:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await bridge.call('logs_diagnose',{'spec':spec,'sha256':sha256},ctx.report_progress)
    @app.tool(structured_output=True)
    async def verify(input:str,sha256:str,rebuild:bool,portable:bool,ctx:Context,trusted_inputs_sha256:str|None=None)->dict[str,Any]:
        """Static portable verification never executes package code. Rebuild requires explicit trusted project-input approval."""
        return await bridge.call('verify',{'input':input,'sha256':sha256,'rebuild':rebuild,'portable':portable,'trusted_inputs_sha256':trusted_inputs_sha256},ctx.report_progress)
    return app
