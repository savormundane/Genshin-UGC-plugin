"""Chinese creator questions and CLI/MCP checks for source-bound lookup."""

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mcp import Client, StdioServerParameters
from PIL import Image, ImageDraw

from authoring_io import PLUGIN, read_json, write_json
import knowledge
from node_build import catalog
from platform_profiles import search


VISIBLE = 'ClientUIBaseControl.SetVisible'
BUTTON_LISTENER = 'ClientUIPresetButtonControl.AddCursorEventListener'
CURSOR_EVENT = 'Enum.CursorEventType'
COMBINED_QUESTION = '按钮点击后怎么隐藏界面'

API_CASES = (
    ('隐藏控件', (VISIBLE,)),
    ('按钮点击', (BUTTON_LISTENER, CURSOR_EVENT)),
    ('设置位置', ('ClientUIBaseControl.SetAnchoredPosition',)),
    (COMBINED_QUESTION, (BUTTON_LISTENER, CURSOR_EVENT, VISIBLE)),
    ('点按钮时怎么绑定点击事件', (BUTTON_LISTENER, CURSOR_EVENT)),
    ('怎么停用控件，让挂载脚本也停止', ('ClientUIBaseControl.SetActive',)),
    ('怎么监听按键事件', ('ClientUIBaseControl.AddKeyEventListener',)),
    ('怎么接收服务器信号', ('Script.RegisterServerSignalHandler',)),
    ('脚本逐帧更新时应该用哪个回调', ('OnUpdate',)),
    ('完成点击', (CURSOR_EVENT,)),
    ('Lua 能访问 Windows 剪贴板吗', ()),
    ('能把本地PNG直接上传到资源库吗', ()),
)

# The second column is the explicit keyword rewrite for tools that take terms.
DOCUMENT_CASES = (
    ('7.2 里实体的定时器有哪些限制', '定时器', 'mhufb90zbnts', '7.2'),
    ('7.2 的资料里，点击按钮后隐藏控件应参考哪一篇', '控件 可见性', 'mhtakr07vej4', '7.1'),
    ('7.2 的自定义拍照按钮在哪份文档里', '自定义按钮控件', 'mhtpwgitsigc', '7.2'),
    ('7.2 的创建实体端口在哪查', '执行节点 创建实体', 'mhw66orrrfkm', '7.1'),
    ('7.2 能把本地 PNG 上传到资源库吗', '本地 PNG 资源库', None, None),
)
NODE_CASES = (
    ('创建实体要接什么', '创建实体', 'server', True),
    ('启动定时器要哪几个参数', '启动定时器', 'server', True),
    ('定时器到点之后用哪个事件', '定时器触发时', 'server', True),
    ('客户端节点图里能找到创建实体吗', '创建实体', 'client', False),
)
ASSET_CASES = (
    ('这张 PNG 转成图元后有几个控件', {}),
    ('20 个控件以内还有什么预览方案', {'max_controls': 20}),
    ('在游戏里用 Lua 直接加载本地 PNG 要查哪个 API', None),
)


def cli(*args):
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(PLUGIN / 'scripts/qianxing.py'), *args],
                            check=True, capture_output=True, encoding='utf-8', timeout=40)
    return json.loads(result.stdout)


class ChineseLookupTests(unittest.TestCase):
    def test_chinese_api_returns_top_three_with_source_evidence(self):
        for question, expected in API_CASES:
            with self.subTest(question=question):
                result = knowledge.api(question)
                self.assertEqual(result['query'], question)
                self.assertEqual((result['editor'], result['host']), ('not_checked', 'not_checked'))
                rows = result['matches']
                if not expected:
                    self.assertEqual((result['status'], rows), ('not_checked', []))
                    self.assertIn('重查', result['retry_hint'])
                    continue
                top = {row['symbol']: row for row in rows[:3]}
                self.assertEqual(result['status'], 'passed')
                self.assertTrue(set(expected) <= top.keys(), list(top))
                self.assertEqual(len(rows), len({row['symbol'] for row in rows}))
                for symbol in expected:
                    row = top[symbol]
                    source = row['source']
                    self.assertEqual(source['integrity'], 'passed')
                    self.assertIsNone(source['version'])
                    self.assertEqual(source['related_official_document']['source_version'], '7.1')
                    self.assertIn(row['knowledge_status'], ('documented', 'derived', 'unknown'))
                    lines = (PLUGIN / source['path']).read_text(encoding='utf-8-sig').splitlines()
                    self.assertTrue(row['description'])
                    self.assertIn(row['description'], lines[row['line'] - 1].replace('`', ''))
                if CURSOR_EVENT in expected:
                    self.assertEqual(top[CURSOR_EVENT]['matched_values'][0]['value'], 'CursorClick')
                    self.assertFalse(any('SimulateCursorClick' in candidate for candidate in top))

    def test_formal_symbols_catalogue_and_digest_stay_compatible(self):
        exact = knowledge.api(VISIBLE)['matches']
        self.assertEqual([(row['symbol'], row['match_basis']) for row in exact], [(VISIBLE, 'symbol_exact')])
        mentioned = knowledge.api('ClientUIBaseControl:SetVisible 怎么用，能监听按钮点击吗')['matches']
        self.assertEqual((mentioned[0]['symbol'], mentioned[0]['match_basis']), (VISIBLE, 'symbol_mention'))
        fragment = knowledge.api('Color')['matches']
        self.assertEqual(fragment[0]['symbol'], '_G.Color')
        self.assertTrue(all(row['match_basis'] == 'symbol_fragment' for row in fragment))
        field, = knowledge.api('ClientUIBaseControl.anchoredPositionX')['matches']
        self.assertEqual(field['type'], 'number')
        self.assertIn('位置', field['description'])
        self.assertTrue(knowledge.api('active')['conflicts'])
        enumeration, = knowledge.api(CURSOR_EVENT)['matches']
        self.assertIn('CursorClick', enumeration['values'])
        member, = knowledge.api('Enum.CursorEventType.CursorClick')['matches']
        self.assertEqual((member['symbol'], member['matched_values'][0]['value']), (CURSOR_EVENT, 'CursorClick'))
        snapshot = knowledge.snapshot()['client_api']
        self.assertEqual(snapshot['enums'][CURSOR_EVENT], enumeration['values'])
        self.assertNotIn('description', snapshot['callbacks']['OnUpdate'])
        self.assertNotIn('enum_members', snapshot)
        with tempfile.TemporaryDirectory(prefix='qianxing knowledge ') as temporary:
            registry = Path(temporary) / 'registry.json'
            data = read_json(knowledge.REGISTRY)
            data['sources']['client_api']['sha256'] = '0' * 64
            write_json(registry, data)
            with patch.object(knowledge, 'REGISTRY', registry), self.assertRaisesRegex(ValueError, 'source changed'):
                knowledge.api('隐藏控件')

    def test_versioned_documents_found_after_keyword_retry(self):
        self.assertEqual(search('7.2', COMBINED_QUESTION)['matches'], 0)
        for question, terms, expected, source_version in DOCUMENT_CASES:
            with self.subTest(question=question, terms=terms):
                result = search('7.2', terms)
                if expected is None:
                    self.assertEqual(result['matches'], 0)
                    continue
                rows = {row['id']: row for row in result['documents'][:5]}
                self.assertIn(expected, rows)
                selected = rows[expected]
                self.assertEqual(selected['requested_version'], '7.2')
                self.assertEqual(selected['source_version'], source_version)
                self.assertEqual(selected['inherited'], source_version != '7.2')
                self.assertTrue(selected['excerpts'] and selected['official_url'])

    def test_chinese_node_questions_keep_the_selected_scope(self):
        for question, term, scope, expected in NODE_CASES:
            with self.subTest(question=question, scope=scope):
                result = catalog(term, scope)
                if expected:
                    self.assertEqual((result['nodes'][0]['name'], result['nodes'][0]['scope']), (term, scope))
                    self.assertTrue(result['nodes'][0]['implementation'])
                else:
                    self.assertEqual(result['matches'], 0)
                    self.assertIn('scope=all', result['hint'])

    def test_mcp_matches_cli_and_routes_asset_questions(self):
        async def run(root):
            project = root / '素材 工程'
            outputs = root / '输出 目录'
            project.mkdir()
            outputs.mkdir()
            filename = '图标 样本.png'
            with Image.new('RGBA', (16, 16)) as image:
                draw = ImageDraw.Draw(image)
                draw.ellipse((1, 1, 14, 14), fill='#d03244')
                draw.rectangle((6, 4, 9, 11), fill='#ffffff')
                image.save(project / filename)

            server = StdioServerParameters(command=sys.executable,
                                           args=['-X', 'utf8', '-B', str(PLUGIN / 'scripts/qianxing.py'), 'mcp', 'serve',
                                                 '--project', str(project), '--output-root', str(outputs)])
            async with Client(server) as client:
                for question in (COMBINED_QUESTION, 'game.LoadAnyLocalPNG'):
                    response = await client.call_tool('api_lookup', {'symbol': question})
                    self.assertFalse(response.is_error, response)
                    self.assertEqual(response.structured_content['result'], cli('knowledge', 'api', question))
                response = await client.call_tool('docs_search', {'version': '7.2', 'query': '控件 可见性'})
                self.assertFalse(response.is_error, response)
                self.assertEqual(response.structured_content['result']['matches'],
                                 cli('docs', 'search', '控件 可见性', '--version', '7.2'))
                response = await client.call_tool('nodes_lookup', {'query': '创建实体', 'scope': 'server'})
                self.assertFalse(response.is_error, response)
                self.assertEqual(response.structured_content['result'], cli('nodes', '创建实体', '--scope', 'server'))

                for index, (question, options) in enumerate(ASSET_CASES):
                    with self.subTest(question=question):
                        if options is None:
                            unknown = await client.call_tool('api_lookup', {'symbol': question})
                            self.assertFalse(unknown.is_error, unknown)
                            result = unknown.structured_content['result']
                            self.assertEqual((result['status'], result['matches']), ('not_checked', []))
                            continue
                        reply = await client.call_tool('asset_preview', {
                            'input': filename, 'output': f'预览 {index}', **options,
                        })
                        self.assertFalse(reply.is_error, reply)
                        report = reply.structured_content['result']
                        self.assertGreater(len(report['candidates']), 1)
                        self.assertTrue(all(type(row['controls']) is int for row in report['candidates']))
                        self.assertTrue(any(item.type == 'image' for item in reply.content))
                        if 'max_controls' in options:
                            self.assertTrue(any(row['within_budget'] for row in report['candidates']))

        with tempfile.TemporaryDirectory(prefix='qianxing Chinese lookup ') as temporary:
            asyncio.run(asyncio.wait_for(run(Path(temporary)), timeout=90))


if __name__ == '__main__':
    unittest.main()
