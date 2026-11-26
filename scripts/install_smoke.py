"""Read-only runtime probes; a local MCP/PNG pass is not Agent or game-host acceptance."""
from pathlib import Path
import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from mcp import Client, StdioServerParameters
from beyond_native import NATIVE_BINARY, native_canvas_environment, read_native_lock, verify_native_files
from miliastra.mcp.bridge import OPERATIONS


async def check(config, node, adapter=None, *, require_render=False):
    bundle = Path(__file__).resolve().parents[1]
    command = node
    args = [str(bundle / 'scripts/mcp_launcher.cjs')]
    env = {**os.environ, 'MILIASTRA_WONDERLAND_RUNTIME_CONFIG': str(config)}
    cwd = None
    if adapter:
        location, root_name, data_name = {
            'agent-plugins': ('mcp.json', 'PLUGIN_ROOT', 'PLUGIN_DATA'),
            'claude-code': ('.mcp.json', 'CLAUDE_PLUGIN_ROOT', 'CLAUDE_PLUGIN_DATA'),
            'codex': ('.codex-plugin/mcp.json', 'PLUGIN_ROOT', 'PLUGIN_DATA'),
        }[adapter]
        config_file = json.loads((bundle / location).read_text(encoding='utf-8'))
        server, = config_file['mcpServers'].values()
        command = node if server['command'] == 'node' else server['command']
        args = [arg.replace('${' + root_name + '}', str(bundle)) for arg in server['args']]
        if adapter == 'codex':
            env = {key: value for key, value in env.items()
                   if not key.startswith('MILIASTRA_WONDERLAND_') or key in server['env_vars']}
        plugin_data = config.parent / 'plugin-data' / adapter
        env.update({key: value.replace('${' + data_name + '}', str(plugin_data))
                    for key, value in server['env'].items()})
        cwd = str(bundle)
    params = StdioServerParameters(command=command, args=args, env=env, cwd=cwd)
    async with Client(params) as client:
        listed = await client.list_tools()
        tools = {tool.name for tool in listed.tools}
        if tools != set(OPERATIONS):
            raise ValueError('MCP 提供的工具与随包操作清单不一致。')
        nodes = await client.call_tool('nodes_lookup', {'query': '启动定时器', 'scope': 'server'})
        if nodes.is_error or not nodes.structured_content['result']['nodes']:
            raise ValueError('MCP 节点查询未成功。')
        doctor = await client.call_tool('doctor', {})
        if doctor.is_error or doctor.structured_content['status'] != 'passed':
            raise ValueError(f'MCP 自检未通过。\n详细原因 {doctor.structured_content!r}')
        for symbol in ('game.GetUICanvasSize', 'OnUpdate'):
            result = await client.call_tool('api_lookup', {'symbol': symbol})
            if result.is_error or result.structured_content['status'] != 'passed':
                raise ValueError('MCP 查询未成功。查询项 ' + symbol)
    backend = bundle / 'vendor/beyond'
    native_lock = read_native_lock(backend)
    software_png = 'not_checked'
    if native_lock is None or verify_native_files(backend, native_lock):
        binding = backend / NATIVE_BINARY if native_lock else None
        with tempfile.TemporaryDirectory(prefix='ugc-smoke-') as td:
            probe = Path(td) / 'render.mjs'
            probe.write_text('import {createStudio} from ' + json.dumps((backend / 'studio/index.js').as_uri()) + ';\n'
                             'import {createDefaultProject} from ' + json.dumps((backend / 'studio/ui/authoring.js').as_uri()) + ';\n'
                             'import {renderPaintPng} from ' + json.dumps((backend / 'studio/host-png.js').as_uri()) + ';\n'
                             'let s=createStudio(createDefaultProject());s.playStart();s.playStep(.1);'
                             'let p=s.playGet({paint:true});let r=renderPaintPng(p.paint,p.canvasWidth,p.canvasHeight);'
                             's.playStop();if(r.data.length<100)throw Error("软件预览返回了空 PNG");console.log(r.data.length);', encoding='utf-8')
            subprocess.run([node, str(probe)], check=True, env=native_canvas_environment(binding))
        software_png = 'passed'
    if require_render and software_png != 'passed':
        raise ValueError('随包 Windows Canvas 未生成软件预览。')
    print(json.dumps({'stdio': 'passed', 'tools': len(tools), 'software_png': software_png,
                      'agent_host': 'not_checked', 'editor': 'not_checked', 'game_host': 'not_checked'}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--node', required=True)
    p.add_argument('--adapter', choices=('agent-plugins', 'claude-code', 'codex'))
    p.add_argument('--require-render', action='store_true')
    args = p.parse_args()
    asyncio.run(asyncio.wait_for(
        check(args.config.resolve(), args.node, args.adapter, require_render=args.require_render),
        timeout=90,
    ))
