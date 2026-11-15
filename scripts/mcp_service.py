"""Official MCP SDK stdio adapter for the shared fixed-operation bridge."""
from importlib.metadata import version
from typing import Any
from mcp.server import MCPServer
from mcp.server.mcpserver import Context


def server(bridge):
    if version('mcp')!='2.3.0':raise ValueError('MCP service requires pinned mcp==2.3.0')
    app=MCPServer('Genshin-UGC')
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
    async def native_inspect(input:str,sha256:str,ctx:Context)->dict[str,Any]:
        """Read native identities from a digest-bound project file."""
        return await bridge.call('native_inspect',{'input':input,'sha256':sha256},ctx.report_progress)
    @app.tool(structured_output=True)
    async def native_audit(input:str,sha256:str,ctx:Context)->dict[str,Any]:
        """Audit final native types and references without modifying input."""
        return await bridge.call('native_audit',{'input':input,'sha256':sha256},ctx.report_progress)
    @app.tool(structured_output=True)
    async def project_inspect(input:str,sha256:str,ctx:Context)->dict[str,Any]:
        """Index native objects and known references; report coverage limits."""
        return await bridge.call('project_inspect',{'input':input,'sha256':sha256},ctx.report_progress)
    @app.tool(structured_output=True)
    async def client_check(input:str,sha256:str,ctx:Context,contract:str|None=None,contract_sha256:str|None=None)->dict[str,Any]:
        """Compile final Lua, optionally checking a digest-bound API contract."""
        args={'input':input,'sha256':sha256}
        if contract is not None:args.update(contract=contract,contract_sha256=contract_sha256)
        elif contract_sha256 is not None:raise ValueError('Contract path required')
        return await bridge.call('client_check',args,ctx.report_progress)
    @app.tool(structured_output=True)
    async def produce(spec:str,sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Build a trusted project into a new output directory; cancellation prevents commit."""
        return await bridge.call('produce',{'spec':spec,'sha256':sha256,'output':output},ctx.report_progress)
    @app.tool(structured_output=True)
    async def native_apply(input:str,sha256:str,plan:str,plan_sha256:str,output:str,ctx:Context)->dict[str,Any]:
        """Apply a reviewed native plan, preserving the original and existing outputs."""
        return await bridge.call('native_apply',{'input':input,'sha256':sha256,'plan':plan,'plan_sha256':plan_sha256,'output':output},ctx.report_progress)
    @app.tool(structured_output=True)
    async def native_diff(input:str,sha256:str,other:str,other_sha256:str,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await bridge.call('native_diff',{'input':input,'sha256':sha256,'other':other,'other_sha256':other_sha256},ctx.report_progress)
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
    async def verify(input:str,sha256:str,rebuild:bool,portable:bool,ctx:Context)->dict[str,Any]:
        """Run the corresponding CLI core with digest-bound inputs and exclusive outputs."""
        return await bridge.call('verify',{'input':input,'sha256':sha256,'rebuild':rebuild,'portable':portable},ctx.report_progress)
    return app
