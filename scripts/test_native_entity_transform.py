"""Public fixture and targeted GIL/GIA transform regressions."""

import asyncio
from pathlib import Path
import sys
import tempfile
import unittest

from authoring_io import DiagnosticError, PLUGIN, read_json, sha
from level_authoring import flt, initial_level, integer, msg, pack, set_section, text, vi
from level_inventory import container, fields, unique, vals
from native_changes import apply_plan, difference, fingerprint, plan
from native_core import get
from project_index import build, consumers

STATIC = 0x40400002
DYNAMIC = 0x40400001  # The template is also DYNAMIC, in a separate namespace.
DECORATION = 0x40000006
STONE = 20001038
SPHERE = 10009002


def label(name, static=False):
    return integer(1, 1) + msg(11, text(1, name) + (integer(2, 1) if static else b''))


def pose(position, rotation, scale):
    vectors = b''.join(
        msg(i, b''.join(flt(axis, value) for axis, value in enumerate(vector, 1) if value)
            + (integer(900, 99) if i == 1 else b''))
        for i, vector in enumerate((position, rotation, scale), 1)
    )
    return integer(1, 1) + msg(11, vectors + integer(501, 0xffffffff)) + text(907, 'unknown component field')


def fixture():
    static_pose = pose((2, 4, -6), (0, 15, 0), (1, 1.5, 2))
    dynamic_pose = pose((-5, 2, 3), (0, 0, 0), (1, 1, 1))
    static = (integer(1, STATIC) + msg(2, integer(1, STONE) + integer(2, 1)) +
              msg(5, label('East terrace', static=True)) + msg(6, static_pose) +
              msg(6, integer(1, 5) + msg(15, integer(1, 1))) + integer(8, STONE) + integer(906, 73))
    links = integer(1, 40) + msg(50, msg(501, vi(DECORATION)))
    dynamic = (integer(1, DYNAMIC) + msg(2, integer(1, DYNAMIC)) + msg(5, label('Gate')) +
               msg(5, links) + msg(6, dynamic_pose) + integer(8, SPHERE))
    template = (integer(1, DYNAMIC) + integer(2, SPHERE) + msg(6, label('Gate template')) +
                msg(7, pose((1, 2, 3), (10, 0, 0), (2, 2, 2))))
    local = (integer(1, DECORATION) + integer(2, 10009009) +
             msg(4, label('Gate cap')) + msg(4, integer(1, 40) + msg(50, integer(502, DYNAMIC))) +
             msg(5, pose((1, 0, -0.5), (20, 0, 0), (1, 1, 1))))
    data = set_section(initial_level('terrace', (2, 2)), 4, msg(1, template))
    data = set_section(data, 5, msg(1, static) + msg(1, dynamic) + integer(908, 74))
    data = set_section(data, 27, msg(2, local))
    gia = pack(msg(1, msg(1, integer(2, 1) + integer(3, 2) + integer(4, STATIC)) +
                   text(3, 'East terrace') + integer(5, 3) + msg(12, msg(1, static) + integer(4, STONE))), (1, 806, 3))
    return data, gia


def selected(data, kind, ident):
    return consumers(build(data), {'kind': kind, 'id': ident})


def patch(data, entity_id, **vectors):
    return {'schema': 2, 'base_sha256': sha(data), 'allowed_top_level_fields': [5],
            'operations': [{'op': 'set_entity_transform', 'section': 5, 'entity_id': entity_id, **vectors}]}


class EntityTransformTests(unittest.TestCase):
    def test_spaces_and_references(self):
        data, gia = fixture()
        placed = selected(data, 'entity', STATIC)
        spatial = placed['target']['spatial']
        self.assertTrue(spatial['static'])
        self.assertEqual(spatial['model']['id'], STONE)
        self.assertEqual(spatial['transform']['position_m'], [2, 4, -6])
        self.assertIn('platform_template', {obj['kind'] for obj in placed['dependencies']})
        custom = selected(data, 'entity', DYNAMIC)
        self.assertEqual(custom['target']['spatial']['template'], {'scope': 'project', 'id': DYNAMIC})
        self.assertEqual(custom['target']['spatial']['model']['id'], SPHERE)
        self.assertFalse(custom['target']['spatial']['static'])
        self.assertEqual(custom['target']['spatial']['transform']['space'], 'world')
        template, = custom['dependencies']
        self.assertEqual(template['kind'], 'template')
        self.assertEqual(template['spatial']['transform']['space'], 'template_default')
        self.assertEqual(template['spatial']['transform']['scale'], [2, 2, 2])
        decoration, = custom['target']['spatial']['decorations']
        self.assertEqual(decoration['transform']['space'], 'owner_local')
        self.assertEqual(decoration['transform']['position_m'], [1, 0, -0.5])
        asset = selected(gia, 'gia_resource', STATIC)['target']['spatial']
        self.assertEqual(asset['transform']['space'], 'asset_world')
        self.assertFalse(asset['transform_editable'])

    def test_partial_edits_keep_unrelated_raw_fields(self):
        data, _ = fixture()
        vectors = {'position_m': [4, 4, -6], 'rotation_deg': [0, 105, 0], 'scale': [2, 1, 0.5]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for requested in ({key: value} for key, value in vectors.items()):
                with self.subTest(requested=requested):
                    proposal = plan(data, patch(data, STATIC, **requested), root, root)
                    result, report = apply_plan(data, proposal, root)
                    _, old = container(data)
                    _, new = container(result)
                    self.assertEqual([raw for n, _, _, raw in old if n != 5], [raw for n, _, _, raw in new if n != 5])
                    old_section = unique(old, 5)
                    new_section = unique(new, 5)
                    a, other_a = vals(fields(old_section), 1)
                    b, other_b = vals(fields(new_section), 1)
                    self.assertEqual(other_a, other_b)
                    self.assertEqual(get(a, 906, 0), get(b, 906, 0))
                    before = get(vals(fields(a), 6)[0], 11)
                    after = get(vals(fields(b), 6)[0], 11)
                    changed_name, = requested
                    for n, key in enumerate(vectors, 1):
                        if key != changed_name:
                            self.assertEqual(get(before, n), get(after, n))
                    self.assertEqual(get(get(after, 1), 900, 0), 99)
                    self.assertEqual(report['operations'][0]['after']['transform'][changed_name], requested[changed_name])
                    self.assertEqual(difference(data, result, [5])['references'], {'added': [], 'removed': []})
                    self.assertTrue(proposal['difference']['protected']['unchanged'])

            with self.assertRaisesRegex(ValueError, 'Base hash mismatch'):
                apply_plan(result, proposal, root)
            for bad in (
                patch(data, STATIC, scale=[1, 0, 1]),
                patch(data, STATIC, scale=[1, 1e-50, 1]),
                patch(data, STATIC, rotation_deg=[0, float('inf'), 0]),
                patch(data, STATIC, position_m=[0, True, 0]),
                patch(data, STATIC),
                {**patch(data, STATIC, **vectors), 'allowed_top_level_fields': []},
            ):
                with self.assertRaises(ValueError):
                    plan(data, bad, root, root)
            original, = [r for r in vals(fields(unique(container(data)[1], 5)), 1) if get(r, 1, 0) == STATIC]
            duplicated = set_section(data, 5, msg(1, original) + msg(1, original))
            with self.assertRaises(DiagnosticError) as error:
                plan(duplicated, patch(duplicated, STATIC, **vectors), root, root)
            self.assertEqual(error.exception.diagnostics[0]['code'], 'native.reference_ambiguous')

    def test_legacy_difference_contract(self):
        data, _ = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            edit = plan(data, patch(data, STATIC, position_m=[4, 4, -6]), root, root)
            variant, _ = apply_plan(data, edit, root)
            (root / 'variant.gil').write_bytes(variant)
            spec = {'schema': 2, 'base_sha256': sha(data), 'allowed_top_level_fields': [5],
                    'operations': [{'op': 'section_from', 'field': 5, 'source': 'variant.gil'}]}
            legacy = plan(data, spec, root, root)
            del legacy['difference']['spatial_objects']
            legacy['plan_sha256'] = fingerprint(legacy)
            self.assertEqual(apply_plan(data, legacy, root)[0], variant)

    def test_write_gate_rejects_uncalibrated_base_and_section_source(self):
        data, gia = fixture()
        unknown = pack(data[20:-4], (2, 806, 2))
        self.assertEqual(container(unknown)[1], container(data)[1])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'calibrated GIL baseline'):
                plan(unknown, patch(unknown, STATIC, position_m=[4, 4, -6]), root, root)
            source = root / 'section.gil'
            spec = {'schema': 2, 'base_sha256': sha(data), 'allowed_top_level_fields': [5],
                    'operations': [{'op': 'section_from', 'field': 5, 'source': source.name}]}
            for other in (unknown, gia):
                source.write_bytes(other)
                with self.assertRaisesRegex(ValueError, 'calibrated GIL baseline'):
                    plan(data, spec, root, root)

    def test_scene_preview_reports_positions_and_partial_coverage(self):
        from scene_preview import preview

        data, _ = fixture()
        section = unique(container(data)[1], 5)
        missing = integer(1, 0x40400003) + msg(2, integer(1, DYNAMIC)) + msg(5, label('Unpositioned'))
        current = set_section(data, 5, section + msg(1, missing))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'before.gil').write_bytes(data)
            (root / 'current.gil').write_bytes(current)
            result = preview(root / 'current.gil', root / 'output', before=root / 'before.gil')
            layout = read_json(root / 'output/layout.json')
            coverage = result['coverage']
            self.assertEqual(layout['coverage'], coverage)
            self.assertEqual(coverage['before']['without_world_position'], 0)
            after = coverage['current']
            self.assertEqual(after['positioned_entities'], 2)
            self.assertEqual(after['without_world_position'], 1)
            self.assertEqual(after['position_markers_only'], 1)
            self.assertEqual(after['whitebox_outlines'], 1)
            self.assertEqual(after['spatial_coverage'], 'not_checked')
            self.assertFalse(after['complete_reference_index'])
            self.assertEqual(result['editor'], 'not_checked')
            self.assertEqual(result['host'], 'not_checked')

    def test_production_model_evidence_requires_the_final_gil(self):
        from authoring_io import write_json
        from level_authoring import register_script
        from production_core import produce

        data, _ = fixture()
        code = b'value = 7\n'
        data, _ = register_script(data, 'main.lua', code)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'base.gil').write_bytes(data)
            (root / 'outside.lua').write_bytes(code)
            write_json(root / 'patch.json', {'schema': 2, 'base_sha256': sha(data),
                                             'allowed_top_level_fields': [], 'operations': []})
            write_json(root / 'job.json', {'schema': 2, 'native': {'base': 'base.gil', 'spec': 'patch.json'},
                                           'simulation': {'spec': 'simulation.json'}})
            for source, out in (('@level', 'bound'), ('outside.lua', 'external')):
                write_json(root / 'simulation.json', {'schema': 2, 'clients': [{'id': 1, 'source': source}],
                           'steps': [], 'assertions': [{'client': 1, 'path': 'value', 'equals': 7}]})
                evidence = produce(root / 'job.json', root / out)['evidence']
                self.assertEqual(evidence['simulation']['status'], 'passed')
                model = evidence['lua_model']
                self.assertEqual(model['model_status'], 'passed')
                if source == '@level':
                    self.assertEqual(model['status'], 'passed')
                    self.assertEqual(evidence['simulation']['artifact_scope'], 'final_gil')
                    self.assertEqual(model['artifact_sha256'], sha((root / out / 'level.gil').read_bytes()))
                    self.assertEqual(model['bindings'][0]['mapping'], 'main.lua')
                else:
                    self.assertEqual(model['status'], 'not_checked')
                    self.assertEqual(evidence['simulation']['artifact_scope'], 'external_or_mixed')
                    self.assertEqual(model['artifact_scope'], 'external_or_mixed')
                    self.assertEqual(model['bindings'][0]['sha256'], sha(code))

    def test_stdio_uses_existing_review_flow(self):
        from mcp import Client, StdioServerParameters

        async def run(root):
            project, outputs = root / 'project', root / 'output'
            project.mkdir()
            outputs.mkdir()
            data, _ = fixture()
            source = project / 'entrance.gil'
            source.write_bytes(data)
            server = StdioServerParameters(command=sys.executable,
                args=['-X', 'utf8', '-B', str(PLUGIN / 'scripts/qianxing.py'), 'mcp', 'serve',
                      '--project', str(project), '--output-root', str(outputs)])
            async with Client(server) as client:
                async def call(name, **args):
                    response = await client.call_tool(name, args)
                    self.assertFalse(response.is_error, response)
                    result = response.structured_content
                    self.assertEqual(result['status'], 'passed', result)
                    return result

                inspection = await call('project_inspect', input=source.name, selector={'key': f'level/entity/{DYNAMIC}'})
                bound = {'input': source.name, 'sha256': inspection['inputs_sha256']['input']}
                self.assertEqual(inspection['result']['target']['spatial']['model']['id'], SPHERE)
                proposal = await call('native_plan', **bound, patch=patch(
                    data, DYNAMIC, position_m=[-3, 2, 3], rotation_deg=[0, 90, 0], scale=[2, 1, 1.5]), output='review')
                self.assertEqual(proposal['result']['difference']['spatial_objects'][0]['after']['transform']['rotation_deg'], [0, 90, 0])
                result = await call('native_apply', **bound, plan=str(Path(proposal['output']) / 'plan.json'),
                                    plan_sha256=proposal['outputs_sha256']['plan.json'], output='edited')
                written = Path(result['output']) / 'level.gil'
                compared = await call('native_diff', **bound, other=str(written), allowed_top_level_fields=[5])
                self.assertTrue(compared['result']['protected']['unchanged'])
                self.assertEqual(compared['result']['spatial_objects'][0]['before']['transform']['position_m'], [-5, 2, 3])
                self.assertEqual(compared['result']['spatial_objects'][0]['after']['transform']['position_m'], [-3, 2, 3])
                self.assertEqual(source.read_bytes(), data)

        with tempfile.TemporaryDirectory(prefix='qianxing-entity-test-') as temporary:
            asyncio.run(run(Path(temporary)))


if __name__ == '__main__':
    unittest.main()
