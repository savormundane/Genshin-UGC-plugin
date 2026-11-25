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

from authoring_io import PLUGIN, read_json, sha, write_json
from miliastra.client.api import analyze
import knowledge
from miliastra.native.scene import OBJECT_ID_START, read_gia, static_gia
from node_build import catalog
from platform_profiles import search, show
from resource_catalogue import catalogue, check as check_resources, search as search_resources
from scene_authoring import build as build_scene, capture_catalogue


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

    def test_compiler_calibration_and_document_provenance(self):
        compiler = catalog('启动定时器', 'server', 1)['nodes'][0]
        self.assertEqual(compiler['source']['source_kind'], 'bundled_graph_code_node_spec')
        self.assertEqual(compiler['source']['sha256'], sha((PLUGIN / compiler['implementation']).read_bytes()))
        self.assertIsNone(compiler['platform_version'])
        self.assertEqual((compiler['editor'], compiler['host']), ('not_checked', 'not_checked'))
        self.assertNotIn('port_evidence', compiler)

        create = catalog('创建实体', 'server', 1)['nodes'][0]
        ports = create['port_evidence']
        self.assertEqual(ports['source_version'], '7.1')
        self.assertEqual(ports['scope'], 'documented_value_ports')
        self.assertEqual([port['name'] for port in ports['documented_inputs']], ['目标GUID', '单位标签索引列表'])
        self.assertEqual(ports['documented_outputs'], [])
        self.assertIsNone(create['platform_version'])
        self.assertTrue(all(port[1] == '流程' for port in create['outputs']))

        for version in ('7.1', '7.2'):
            with self.subTest(version=version):
                source = catalogue(version)['resources'][0]['source']
                document = show(version, 'mh4imrrhzdzi')
                for key in ('source_kind', 'source_version', 'inherited', 'applicability', 'mirror_url', 'commit'):
                    self.assertEqual(source.get(key), document.get(key))

    def test_media_lookup_preserves_version_and_read_only_evidence(self):
        sound = search_resources('7.2', '界面音效 按钮点击', 'sound', 'beyond', limit=1)['resources'][0]
        self.assertEqual((sound['type'], sound['category'], sound['version']), ('sound', '界面音效', '7.1'))
        self.assertEqual(sound['applicability'], 'historical_observation')
        self.assertIsNone(sound['mode'])
        latest, = search_resources('7.2', '10019173', 'effect', 'beyond')['resources']
        self.assertEqual(latest['category'], '限时特效')
        self.assertEqual(latest['reported_duration_s'], 2.91)
        self.assertTrue(latest['name_truncated'])
        self.assertEqual(latest['source']['source_client_version'], '7.2.0')
        self.assertEqual(latest['source']['frame_sha256'],
                         '277380216ac195602b4ec7f3a3f7863163d575c7550644d857d5f639ef574009')
        self.assertEqual(latest['source']['sha256'], sha((PLUGIN / latest['source']['path']).read_bytes()))
        self.assertEqual((latest['native_write_evidence'], latest['host']), ('none', 'not_checked'))
        self.assertEqual(search_resources('7.1', '10019173', 'effect')['matches'], 0)
        with tempfile.TemporaryDirectory(prefix='miliastra resource observation ') as temporary:
            usage = Path(temporary) / 'uses.json'
            write_json(usage, {'schema': 2, 'version': '7.2', 'mode': 'beyond', 'uses': [
                {'type': 'effect', 'id': latest['id'], 'accept_declared': True}
            ]})
            checked = check_resources(usage)
            self.assertEqual(checked['status'], 'failed')
            self.assertEqual(checked['errors'][0]['error'], 'resource absent')

    def test_lua_type_hints_remain_unverified(self):
        navigation = ('local focused = game.GetControllerFocus(); '
                      'local mode, target = focused:GetControllerNavigation(Enum.ControllerNavigationDir.Left); '
                      'target:SetVisible(true)')
        report = analyze(navigation)
        self.assertEqual((report['status'], report['derived_types']), ('not_checked', 'not_checked'))
        self.assertEqual(report['errors'], [])
        self.assertIn('unknown_receiver_type', {row['reason'] for row in report['unresolved']})
        self.assertTrue(any(call['return_basis'] == 'derived' for call in report['calls']))
        self.assertFalse(any(call['name'] == 'SetVisible' for call in report['calls']))

        advised = analyze('game.GetClientUIControl(1):SetVisible("false")')
        self.assertEqual((advised['status'], advised['errors']), ('not_checked', []))
        call = next(row for row in advised['calls'] if row['name'] == 'SetVisible')
        self.assertEqual((call['parameter_basis'], call['parameter_enforced']), (['derived'], [False]))
        self.assertEqual(analyze('script:EnableUpdate("false")')['status'], 'failed')
        passed = analyze('game.GetClientUIControl(1):SetVisible(false)')
        self.assertEqual((passed['status'], passed['derived_types']), ('passed', 'not_checked'))

    def test_model_size_requires_measurement_bound_to_the_native_sample(self):
        with tempfile.TemporaryDirectory(prefix='qianxing dimensions ') as temporary:
            root = Path(temporary)
            sample, models, measurement, layout, uses = (root / name for name in (
                'sample.gia', 'models.json', 'measurement.json', 'layout.json', 'uses.json'))
            template, dimensions = 20001038, [2, 4, 8]
            witness = static_gia([{'record_id': OBJECT_ID_START, 'template_id': template, 'name': 'Fixture',
                                   'position_m': [0, 0, 0], 'rotation_deg': [0, 0, 0], 'scale': [1, 1, 1]}])
            sample.write_bytes(witness)
            capture_catalogue(sample, models, '7.2', 'beyond')
            model_data = read_json(models)
            record = {'template_id': template, 'dimensions_m': dimensions}
            target = {'version': '7.2', 'mode': 'beyond', 'catalogues': [models.name]}
            write_json(layout, {**target, 'schema': 1, 'objects': [{
                'key': 'sample', 'name': 'Fixture', 'template_id': template, 'position_m': [0, 0, 0], 'size_m': [6, 2, 12],
            }]})
            write_json(uses, {**target, 'schema': 2, 'uses': [{'type': 'model', 'id': template, 'dimensions': dimensions}]})

            valid = {'sample_sha256': sha(witness), 'version': '7.2', 'mode': 'beyond', 'method': 'Synthetic fixture'}
            for provenance in ({}, {**valid, 'sample_sha256': '0' * 64}, {**valid, 'version': '7.1'},
                               {**valid, 'mode': 'classic'}, {**valid, 'method': ''}, valid):
                with self.subTest(provenance=provenance):
                    measurement.write_text(json.dumps({**record, **provenance}), encoding='utf-8')
                    model_data['resources'][0].update(dimensions=dimensions, dimensions_source={
                        'path': measurement.name, 'sha256': sha(measurement.read_bytes()),
                    })
                    models.write_text(json.dumps(model_data), encoding='utf-8')
                    output = root / 'result'
                    if provenance != valid:
                        self.assertEqual(check_resources(uses)['status'], 'not_checked')
                        with self.assertRaisesRegex(ValueError, 'bound to the native sample'):
                            build_scene(layout, output)
                        self.assertFalse(output.exists())
                    else:
                        self.assertEqual(check_resources(uses)['status'], 'passed')
                        build_scene(layout, output)
                        result, = read_gia((output / 'scene.gia').read_bytes(), static_only=True)
                        self.assertEqual(result['scale'], [3, 0.5, 1.5])

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
