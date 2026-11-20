"""Small neutral fitting and portable checks shared by candidate preparation and CI."""

import json
from importlib.util import find_spec
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, PngImagePlugin

from asset_fit import build, fit, parameters
from asset_fit_v2 import residual_index
from authoring_io import inventory, write_json
from delivery_verify import verify


class ReleaseBehaviorTests(unittest.TestCase):
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
                with self.assertRaisesRegex(ValueError, 'current trusted'):
                    verify(root, True, True, report['trusted_inputs_sha256'])
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
