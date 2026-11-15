"""Read-only runtime probes; a local MCP/PNG pass is not Agent or game-host acceptance."""
from pathlib import Path
import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from mcp import Client, StdioServerParameters


async def check(config, node):
    bundle = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(command=node, args=[str(bundle / 'scripts/mcp_launcher.cjs')],
                                   env={**os.environ, 'UGC_RUNTIME_CONFIG': str(config)})
    async with Client(params) as client:
        listed = await client.list_tools()
        if len(listed.tools) != 18:
            raise ValueError('Expected 18 MCP tools')
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
    print(json.dumps({'stdio': 'passed', 'tools': 18, 'software_png': 'passed',
                      'agent_host': 'not_checked', 'editor': 'not_checked', 'game_host': 'not_checked'}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--node', required=True)
    args = p.parse_args()
    asyncio.run(asyncio.wait_for(check(args.config, args.node), timeout=90))
