"""Small neutral fitting and portable checks shared by candidate preparation and CI."""

import json
from importlib.util import find_spec
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, PngImagePlugin

from miliastra.assets.fit import build, fit, parameters
from miliastra.assets.fit_residual import residual_index
from authoring_io import PLUGIN, inventory, read_json, sha, write_json
from delivery_verify import verify


class ReleaseBehaviorTests(unittest.TestCase):
    @unittest.skipUnless(find_spec('lupa') and find_spec('lupa.lua53'), 'Lua compile check requires lupa.lua53')
    def test_gil_bound_fit_creates_reviewed_mount(self):
        from joint_simulator import script_from_gil
        from level_authoring import compile_spec
        from miliastra.native.changes import apply_plan, plan
        from portable_delivery import collect
        from production_core import produce

        sample = PLUGIN / 'samples/creator-demos/png'
        png = sample / 'checkpoint-marker.png'
        with tempfile.TemporaryDirectory(prefix='miliastra mounted fit ') as temporary:
            root = Path(temporary)
            existing = 'function OnStart() end\n'
            (root / 'existing.lua').write_bytes(existing.encode('utf-8'))
            raw, initial = compile_spec({
                'schema': 'qianxing-level-spec/v1', 'id': 'existing', 'map_size': [2, 2],
                'root_script': 'existing.lua',
                'scripts': [{'name': 'existing.lua', 'source': 'existing.lua'}],
                'templates': [{'name': 'MarkerRect', 'kind': 'image', 'size': [24, 24]},
                              {'name': 'WrongKind', 'kind': 'container', 'size': [24, 24]}],
            }, root)
            gil = root / 'original.gil'
            gil.write_bytes(raw)
            control = min(row['control_guid'] for row in initial['script_bindings'])
            source_sha = sha(raw)
            config = read_json(sample / 'fit.json')
            config['mount'] = {'gil': gil.name, 'sha256': source_sha,
                               'control': control, 'template': 'MarkerRect', 'width': 144, 'height': 144}
            fit_file, fit_output = root / 'fit.json', root / 'fitted'
            for patch, message in (
                ({'sha256': '0' * 64}, '关卡摘要已变化'),
                ({'control': 'Root'}, '挂载控件须唯一匹配'),
                ({'template': 'WrongKind'}, '图片模板须有唯一'),
            ):
                write_json(fit_file, {**config, 'mount': {**config['mount'], **patch}})
                with self.assertRaisesRegex(ValueError, message):
                    build(png, fit_file, fit_output)
                self.assertFalse(fit_output.exists())
            write_json(fit_file, config)
            result = build(png, fit_file, fit_output)
            mount = result['mount']
            self.assertEqual(mount['gil_binding']['control_guid'], control)
            self.assertEqual(mount['gil_binding']['template_index'], initial['template_indices']['MarkerRect'])
            self.assertEqual(result['inputs'][str(gil)], source_sha)
            self.assertEqual(mount['preview_binding'], 'explicit_software_template')
            self.assertEqual(read_json(fit_output / 'beyond.json')['scripts'][0]['sha256'], mount['sha256'])
            self.assertGreater(sum(layer['controls'] for layer in result['layers']), 0)
            self.assertLessEqual(sum(layer['controls'] for layer in result['layers']), 20)

            mapping = 'marker.lua'
            attach = {'op': 'bind_client_lua', 'control_guid': control, 'mapping': mapping,
                      'source': 'fitted/mounted.lua', 'fit_catalog': 'fitted/catalog.json'}
            patch = {'schema': 2, 'base_sha256': source_sha, 'allowed_top_level_fields': [9, 50],
                     'operations': [attach]}
            sealed = plan(raw, patch, root, root)
            self.assertEqual(set(sealed['inputs']), {'@input:0', '@input:0:fit_catalog'})
            edited, report = apply_plan(raw, sealed, root)
            self.assertTrue(report['protected_fields_unchanged'])
            self.assertEqual({int(row['key']) for row in sealed['difference']['top_level_fields']}, {9, 50})
            self.assertEqual(gil.read_bytes(), raw)
            embedded, after = script_from_gil(edited, mapping)
            self.assertEqual(sha(embedded.encode('utf-8')), mount['sha256'])
            self.assertEqual(script_from_gil(edited, 'existing.lua')[0], existing)
            script = next(row for row in after['scripts'] if row['name'] == mapping)
            self.assertIn({'control_guid': control, 'control_name': mount['gil_binding']['control_name'],
                           'script_guid': script['id'], 'mapping_found': True}, after['script_bindings'])
            with self.assertRaisesRegex(ValueError, '脚本映射已存在'):
                plan(raw, {**patch, 'operations': [{**attach, 'mapping': 'existing.lua'}]}, root, root)

            input_image = root / png.name
            shutil.copyfile(png, input_image)
            patch_file, job_file, delivered = root / 'patch.json', root / 'job.json', root / 'delivered'
            write_json(patch_file, {**patch, 'operations': [
                {'op': 'bind_client_lua', 'mapping': mapping, 'source': '@asset:marker'},
            ]})
            write_json(job_file, {
                'schema': 2, 'assets': [{'name': 'marker', 'kind': 'fit', 'source': input_image.name,
                                          'spec': fit_file.name}],
                'native': {'base': gil.name, 'spec': patch_file.name},
            })
            _, _, _, configs, bindings, _ = collect(job_file, {})
            self.assertEqual(configs[fit_file][0], 'fit_spec')
            self.assertTrue(any(path == fit_file and key == 'gil' and value == gil
                                for path, _, key, value in bindings))
            produce(job_file, delivered)
            final = (delivered / 'level.gil').read_bytes()
            self.assertEqual(final, edited)
            self.assertEqual(gil.read_bytes(), raw)
            operation, = read_json(delivered / 'native-report.json')['operations']
            self.assertEqual(operation['control_guid'], control)
            self.assertEqual(operation['lua_sha256'], mount['sha256'])

            (fit_output / 'mounted.lua').write_text('function OnStart() end\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'plan input digest changed'):
                apply_plan(raw, sealed, root)

    @unittest.skipUnless(find_spec('lupa') and find_spec('lupa.lua53'), 'checkpoint sample requires lupa.lua53')
    def test_checkpoint_marker_sample_mounts_and_reuses_rectangles(self):
        from lupa.lua53 import LuaError, LuaRuntime

        from joint_simulator import script_from_gil
        from miliastra.assets.pipeline import generate
        from miliastra.client.assembly import assemble

        sample = PLUGIN / 'samples/creator-demos/png'
        mapping = 'checkpoint-marker.lua'
        source = (sample / mapping).read_bytes()
        unconfigured = 'local RECT_TEMPLATE_INDEX = 0'
        self.assertEqual(source.decode('utf-8').count(unconfigured), 1)
        stock_data = (sample / 'generated/data.lua').read_text(encoding='utf-8-sig').rstrip()
        with tempfile.TemporaryDirectory(prefix='miliastra checkpoint ') as temporary:
            root = Path(temporary)
            (root / 'marker-data.lua').write_text(
                '-- BEGIN MARKER DATA\nlocal MARKER = (function()\n' + stock_data +
                '\nend)()\n-- END MARKER DATA\n',
                encoding='utf-8', newline='\n',
            )
            renderer = sample / 'checkpoint-marker-render.lua'
            shutil.copyfile(renderer, root / renderer.name)
            assembled, _ = assemble({
                'schema': 2, 'modules': [{'name': 'ui', 'as': 'UI'}],
                'sources': [{'id': 'marker-data', 'source': 'marker-data.lua'},
                            {'id': 'marker-draw', 'source': renderer.name,
                             'requires': ['UI', 'marker-data']}],
            }, root)
            self.assertEqual(source, assembled.encode('utf-8'))
            spec_path = root / 'level.json'
            spec = {
                'schema': 'qianxing-level-spec/v1', 'id': 'checkpoint-marker',
                'map_size': [2, 2],
                'templates': [{'name': 'MarkerRect', 'kind': 'image', 'size': [24, 24]},
                              {'name': 'WrongKind', 'kind': 'container', 'size': [24, 24]}],
            }
            cli = [sys.executable, '-X', 'utf8', '-B', str(PLUGIN / 'scripts/qianxing.py')]

            def command(*args):
                result = subprocess.run(
                    [*cli, *map(str, args)], capture_output=True, encoding='utf-8', timeout=45,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return json.loads(result.stdout)

            write_json(spec_path, spec)
            seed = command('level', 'create', spec_path, '--out', root / 'templates.gil')
            index = seed['template_indices']['MarkerRect']
            configured = f'local RECT_TEMPLATE_INDEX = {index}'
            code = assembled.replace(unconfigured, configured, 1)
            (root / mapping).write_text(code, encoding='utf-8', newline='\n')
            write_json(spec_path, {**spec, 'root_script': mapping,
                                   'scripts': [{'name': mapping, 'source': mapping}]})
            level = root / 'checkpoint-marker.gil'
            command('level', 'create', spec_path, '--out', level)
            embedded, bindings = script_from_gil(level.read_bytes(), mapping)
            self.assertEqual(embedded, code)
            self.assertEqual(bindings['diagnostics'], [])
            self.assertTrue(any(row['name'] == 'MarkerRect' and row['kind'] == 'image'
                                and row['template_guid'] == index and row['reciprocal_reference_verified']
                                for row in bindings['templates']))
            script_id, = [row['id'] for row in bindings['scripts'] if row['name'] == mapping]
            self.assertTrue(any(row['script_guid'] == script_id and row['mapping_found']
                                for row in bindings['script_bindings']))
            self.assertEqual(command('client', 'check', level, '--mapping', mapping)['checks']['syntax'], 'passed')
            startup = command('simulate', 'check', level, '--mapping', mapping)
            self.assertEqual(startup['live_controls'], 12)
            self.assertIn('检查点已创建 11 个矩形。', startup['logs'])

            model_source = (PLUGIN / 'scripts/client_simulator.lua').read_text(encoding='utf-8')

            def loaded_model(script):
                lua = LuaRuntime(unpack_returned_tuples=True, register_eval=False, register_builtins=False)
                model = lua.execute(model_source)
                templates = {row['template_guid']: lua.table(name=row['name'], kind=row['kind'])
                             for row in bindings['templates']}
                model.setup(lua.table(), lua.table(width=1600, height=900, mapping=mapping, scriptId=script_id,
                                                    templates=lua.table_from(templates)))
                model.load(script)
                return model

            model = loaded_model(embedded)
            model.boot()
            children = model.root.GetChildren(model.root)
            self.assertEqual(len(children), 11)
            tiles = [children[i] for i in range(1, len(children) + 1)]
            asset = json.loads((sample / 'generated/asset.json').read_text(encoding='utf-8'))['data']
            raster = Image.new('RGBA', (144, 144))
            for tile, (x, y, w, h, color_index) in zip(tiles, asset['rects'], strict=True):
                self.assertTrue(tile.active and tile.visible)
                self.assertEqual(tile.prefabIndex, index)
                cx, cy = tile.GetAnchoredPosition(tile)
                width, height = tile.GetSizeDelta(tile)
                box = (72 + cx - width / 2, 72 - cy - height / 2,
                       72 + cx + width / 2, 72 - cy + height / 2)
                self.assertEqual(box, (24 * x, 24 * y, 24 * (x + w), 24 * (y + h)))
                color = tuple(tile.imageColor[channel] for channel in 'rgba')
                self.assertEqual(color, tuple(asset['palette'][color_index - 1]))
                raster.paste(color, tuple(map(int, box)))
            with Image.open(sample / 'preview-grid-25.png') as preview:
                self.assertEqual(raster.tobytes(), preview.convert('RGBA').tobytes())

            ids = [tile.id for tile in tiles]
            for _ in range(2):
                model.requestLifecycle('OnDisable')
                self.assertTrue(all(not tile.visible and tile.active for tile in tiles))
                model.requestLifecycle('OnEnable')
                visible = model.root.GetChildren(model.root)
                self.assertEqual([visible[i].id for i in range(1, len(visible) + 1)], ids)
                self.assertTrue(all(tile.visible for tile in tiles))
            model.requestLifecycle('OnDestroy')
            self.assertTrue(all(not tile.alive for tile in tiles))
            self.assertEqual(len(model.root.GetChildren(model.root)), 0)

            oversize = root / 'oversize'
            generate(sample / 'checkpoint-marker.png', oversize)
            oversized_data = (oversize / 'data.lua').read_text(encoding='utf-8').rstrip()
            for script, error in (
                (assembled, '填入 RECT_TEMPLATE_INDEX'),
                (assembled.replace(unconfigured, 'local RECT_TEMPLATE_INDEX = 1', 1), '模板索引不存在'),
                (assembled.replace(unconfigured,
                                   f"local RECT_TEMPLATE_INDEX = {seed['template_indices']['WrongKind']}", 1),
                 'imageColor'),
                (embedded.replace(stock_data, oversized_data, 1), '超过示例预算'),
            ):
                rejected = loaded_model(script)
                with self.assertRaisesRegex(LuaError, error):
                    rejected.boot()
                self.assertEqual(len(rejected.root.GetChildren(rejected.root)), 0)

    def test_fit_dimensions_before_decode(self):
        with tempfile.TemporaryDirectory(prefix='ugc fit ') as temporary:
            root = Path(temporary)
            allowed = root / 'limit.png'
            oversized = root / 'over-limit.png'
            Image.new('RGBA', (512, 512)).save(allowed)
            Image.new('RGBA', (513, 512)).save(oversized)
            spec = root / 'fit.json'
            write_json(spec, {'schema': 2, 'work': 1, 'max_controls': 2})
            build(allowed, spec, root / 'valid')
            self.assertTrue((root / 'valid/image/preview.png').is_file())

            original_load = PngImagePlugin.PngImageFile.load

            def deny_oversized_decode(image, *args, **kwargs):
                if image.size == (513, 512):
                    raise AssertionError('oversized image reached pixel decoding')
                return original_load(image, *args, **kwargs)

            layers = root / 'layers.json'
            write_json(layers, {'schema': 1, 'layers': [
                {'name': 'good', 'source': allowed.name},
                {'name': 'bad', 'source': oversized.name},
            ]})
            with patch.object(PngImagePlugin.PngImageFile, 'load', deny_oversized_decode):
                for source in (oversized, layers):
                    with self.subTest(source=source.name):
                        output = root / 'rejected'
                        with self.assertRaisesRegex(ValueError, r'over-limit\.png: 513x512 exceeds 262144'):
                            build(source, spec, output)
                        self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, 'Fit schema 1 or 2'):
                parameters({'schema': 3})

    @unittest.skipUnless(find_spec('lupa') and find_spec('lupa.lua53'), 'full production requires lupa.lua53')
    def test_production_rejects_oversized_layer_without_output(self):
        from production_core import produce

        with tempfile.TemporaryDirectory(prefix='ugc production fit ') as temporary:
            root = Path(temporary)
            Image.new('RGBA', (513, 512)).save(root / 'over-limit.png')
            write_json(root / 'layers.json', {'schema': 1, 'layers': [{'name': 'oversized', 'source': 'over-limit.png'}]})
            write_json(root / 'fit.json', {'schema': 2, 'work': 1})
            job = root / 'job.json'
            write_json(job, {'schema': 2, 'assets': [
                {'kind': 'fit', 'name': 'neutral', 'source': 'layers.json', 'spec': 'fit.json'},
            ]})
            with self.assertRaisesRegex(ValueError, r'over-limit\.png: 513x512 exceeds 262144'):
                produce(job, root / 'production')
            self.assertFalse((root / 'production').exists())

    def test_residual_sampler_rounding_boundary(self):
        self.assertEqual(residual_index([0, 4, 4, 12, 12, 12], 1.0), 3)
        self.assertEqual(residual_index([0, 4, 4, 8], 0.5), 3)
        self.assertEqual(residual_index([0, 4, 4, 8], 0.0), 1)

    def test_fit_budget_and_resume(self):
        image = Image.new('RGBA', (12, 8), (55, 90, 130, 180))
        config = parameters({'schema': 2, 'shapes': ['line'], 'work': 80, 'budget': 8, 'seed': 19, 'max_controls': 6})
        one, one_image = fit(image, config, 'neutral')
        part, _ = fit(image, config, 'neutral', steps=17)
        self.assertEqual(part['work_done'], 17)
        resumed, resumed_image = fit(image, config, 'neutral', state=json.loads(json.dumps(part)))
        self.assertEqual(one, resumed)
        self.assertEqual(one_image.tobytes(), resumed_image.tobytes())
        self.assertGreater(one['history'][-1][1], 0)
        self.assertTrue(all(cost <= 6 for _, cost in one['history']))

    def test_portable_static_and_refusals(self):
        with tempfile.TemporaryDirectory(prefix='ugc portable ') as temporary:
            root = Path(temporary)
            bundle = root / 'portable'
            tools = bundle / 'workspace/toolchain/scripts'
            project = bundle / 'workspace/project'
            tools.mkdir(parents=True)
            project.mkdir(parents=True)
            write_json(project / 'job.json', {'schema': 2})
            stub = tools / 'qianxing.py'
            stub.write_text('raise RuntimeError("static verification must not execute this file")\n', encoding='utf-8')
            write_json(bundle / 'portable.json', {'schema': 1, 'job': 'project/job.json', 'files': inventory(bundle)})
            write_json(root / 'manifest.json', {
                'schema': 2, 'kind': 'production', 'inputs': {}, 'files': inventory(root),
                'portable': {'schema': 1, 'root': 'portable'},
            })
            with patch('subprocess.run', side_effect=AssertionError('verification launched a subprocess')):
                report = verify(root, portable=True)
                self.assertTrue(report['passed'])
                self.assertEqual(report['rebuild'], 'not_checked')
                with self.assertRaisesRegex(ValueError, 'current trusted') as mismatch:
                    verify(root, True, True, report['trusted_inputs_sha256'])
                reason, = mismatch.exception.diagnostics
                self.assertEqual(reason['code'], 'portable.toolchain_mismatch')
                self.assertNotEqual(reason['expected'], reason['actual'])
                extra = project / 'unregistered.txt'
                extra.write_text('neutral', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'Unregistered'):
                    verify(root, portable=True)
                extra.unlink()
                stub.write_text('# changed', encoding='utf-8')
                with self.assertRaises(ValueError):
                    verify(root, portable=True)


if __name__ == '__main__':
    unittest.main()
