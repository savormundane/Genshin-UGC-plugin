"""Read-only runtime probes; a local MCP/PNG pass is not Agent or game-host acceptance."""
from pathlib import Path
import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from mcp import Client, StdioServerParameters
from mcp_bridge import OPERATIONS


async def check(config, node, adapter=None):
    bundle = Path(__file__).resolve().parents[1]
    command = node
    args = [str(bundle / 'scripts/mcp_launcher.cjs')]
    env = {**os.environ, 'UGC_RUNTIME_CONFIG': str(config)}
    cwd = None
    if adapter == 'deepseek-harness':
        patch = json.loads((bundle.parent / 'cordis-bundle/cordis.patch.yml').read_text(encoding='utf-8'))
        server = next(row['config'] for row in patch[0]['insert'] if row['name'] == '@deepseek-ai/dsh-mcp-client')
        command, args, cwd = server['command'], server['args'], server['cwd']
        env.update(server['env'])
    elif adapter:
        location = '.mcp.json' if adapter == 'claude-code' else 'mcp.json'
        placeholder = '${CLAUDE_PLUGIN_ROOT}' if adapter == 'claude-code' else '${PLUGIN_ROOT}'
        config_file = json.loads((bundle / location).read_text(encoding='utf-8'))
        server, = config_file['mcpServers'].values()
        command = server['command']
        args = [arg.replace(placeholder, str(bundle)) for arg in server['args']]
        env.update(server['env'])
        cwd = str(bundle)
    params = StdioServerParameters(command=command, args=args, env=env, cwd=cwd)
    async with Client(params) as client:
        listed = await client.list_tools()
        tools = {tool.name for tool in listed.tools}
        if tools != set(OPERATIONS):
            raise ValueError('MCP tools differ from the bundled operation list')
        nodes = await client.call_tool('nodes_lookup', {'query': '启动定时器', 'scope': 'server'})
        if nodes.is_error or not nodes.structured_content['result']['nodes']:
            raise ValueError('MCP node lookup failed')
        doctor = await client.call_tool('doctor', {})
        if doctor.is_error or doctor.structured_content['status'] != 'passed':
            raise ValueError(f'MCP worker cannot diagnose the configured runtime: {doctor.structured_content!r}')
        for symbol in ('game.GetUICanvasSize', 'OnUpdate'):
            result = await client.call_tool('api_lookup', {'symbol': symbol})
            if result.is_error or result.structured_content['status'] != 'passed':
                raise ValueError('MCP lookup failed: ' + symbol)
    backend = bundle / 'vendor/beyond'
    with tempfile.TemporaryDirectory(prefix='ugc-smoke-') as td:
        probe = Path(td) / 'render.mjs'
        probe.write_text('import {createStudio} from ' + json.dumps((backend / 'studio/index.js').as_uri()) + ';\n'
                         'import {createDefaultProject} from ' + json.dumps((backend / 'studio/ui/authoring.js').as_uri()) + ';\n'
                         'import {renderPaintPng} from ' + json.dumps((backend / 'studio/host-png.js').as_uri()) + ';\n'
                         'let s=createStudio(createDefaultProject());s.playStart();s.playStep(.1);'
                         'let p=s.playGet({paint:true});let r=renderPaintPng(p.paint,p.canvasWidth,p.canvasHeight);'
                         's.playStop();if(r.data.length<100)throw Error("empty PNG");console.log(r.data.length);', encoding='utf-8')
        subprocess.run([node, str(probe)], check=True)
    print(json.dumps({'stdio': 'passed', 'tools': len(tools), 'software_png': 'passed',
                      'agent_host': 'not_checked', 'editor': 'not_checked', 'game_host': 'not_checked'}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--node', required=True)
    p.add_argument('--adapter', choices=('agent-plugins', 'deepseek-harness', 'claude-code', 'codex'))
    args = p.parse_args()
    asyncio.run(asyncio.wait_for(check(args.config, args.node, args.adapter), timeout=90))
