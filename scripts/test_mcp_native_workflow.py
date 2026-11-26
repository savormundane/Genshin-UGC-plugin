"""Public fixture for a reviewed template edit over the real MCP stdio transport."""

import asyncio
from base64 import b64decode
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lupa.lua53 import LuaRuntime
from mcp import Client, StdioServerParameters, types
from PIL import Image

from authoring_io import PLUGIN, read_json, sha, sha_file, write_json
from level_authoring import initial_level, integer, msg, set_section, text

TEMPLATE = 0x40C00001
INSTANCE = 0x40400001
VARIABLE = "ActivationDelay"


def entrance_fixture():
    """A small level with one placed object inheriting a template parameter."""
    descriptor = integer(1, 3) + msg(2)
    value = integer(1, 3) + msg(2, descriptor) + msg(13, integer(1, 7))
    variable = text(2, VARIABLE) + integer(3, 3) + msg(4, value) + integer(5, 1) + msg(6, descriptor)
    group = integer(1, 1) + integer(2, 1) + msg(11, msg(1, variable))
    template = integer(1, TEMPLATE) + msg(8, group)
    instance = integer(1, INSTANCE) + msg(2, integer(1, TEMPLATE) + integer(2, 0))
    level = set_section(initial_level("entrance", (2, 2)), 4, msg(1, template))
    return set_section(level, 5, msg(1, instance))


class NativeWorkflowTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="qianxing public workflow ")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.root = root
        self.project = root / "project"
        self.outputs = root / "outputs"
        self.project.mkdir()
        self.outputs.mkdir()
        self.raw = entrance_fixture()
        (self.project / "entrance.gil").write_bytes(self.raw)
        self.server = StdioServerParameters(
            command=sys.executable,
            args=["-X", "utf8", "-B", str(PLUGIN / "scripts/qianxing.py"), "mcp", "serve",
                  "--project", str(self.project), "--output-root", str(self.outputs)],
        )

    def workspace_environment(self):
        env = {key: value for key, value in os.environ.items()
               if key not in ('MILIASTRA_WONDERLAND_PROJECT_ROOT', 'MILIASTRA_WONDERLAND_OUTPUT_ROOT', 'MILIASTRA_WONDERLAND_RUNTIME_CONFIG', 'MILIASTRA_WONDERLAND_PYTHON')}
        env['MILIASTRA_WONDERLAND_PLUGIN_DATA'] = str(self.root / 'plugin-data')
        return env

    async def call(self, client, tool, params, status="passed"):
        outcome = await client.call_tool(tool, params)
        self.assertFalse(outcome.is_error, outcome)
        self.assertEqual(outcome.structured_content["status"], status, outcome)
        return outcome.structured_content

    def test_tool_metadata_and_compact_capabilities(self):
        async def run():
            async with Client(self.server) as client:
                listed = await client.list_tools()
                self.assertEqual(client.server_info.version, read_json(PLUGIN / "plugin.json")["version"])
                tools = {tool.name: tool for tool in listed.tools}
                for tool in tools.values():
                    with self.subTest(tool=tool.name):
                        self.assertTrue(tool.description)
                        self.assertIsNotNone(tool.annotations)
                        for name, schema in tool.input_schema["properties"].items():
                            self.assertTrue(schema.get("description"), name)

                annotations = {name: tool.annotations.model_dump(by_alias=True) for name, tool in tools.items()}
                self.assertTrue(annotations["docs_search"]["readOnlyHint"])
                self.assertFalse(annotations["asset_preview"]["readOnlyHint"])
                self.assertFalse(annotations["asset_preview"]["destructiveHint"])
                self.assertFalse(annotations["experiment_run"]["readOnlyHint"])
                self.assertTrue(annotations["experiment_compare"]["readOnlyHint"])
                self.assertIn("observations.json", tools["experiment_run"].description)
                self.assertIn("配对比较", tools["experiment_compare"].description)

                outcome = await client.call_tool("capabilities", {})
                self.assertFalse(outcome.is_error, outcome)
                self.assertLess(sum(len(part.text) for part in outcome.content), 8192)
                result = outcome.structured_content["result"]
                self.assertEqual(result["version"], read_json(PLUGIN / "plugin.json")["version"])
                self.assertEqual(result["tasks"]["nodes"], ["nodes_lookup", "graph_check", "graph_build"])
                routed = {tool for group in result["tasks"].values() for tool in group}
                self.assertEqual(routed | set(result["other_tools"]), set(tools))
                self.assertEqual(result["validation"]["editor"], "not_checked")
                self.assertEqual(result["validation"]["host"], "not_checked")
                self.assertIn("--evidence", result["detail_command"])

        asyncio.run(run())

    @unittest.skipUnless(shutil.which("node"), "Node.js required for runtime fingerprint coverage")
    def test_portable_production_and_rebuild_over_stdio(self):
        from qianxing_workflow import check

        source = self.project / "client.lua"
        source.write_text("function OnInit() end\n", encoding="utf-8")
        write_json(self.project / "level.json", {
            "schema": "qianxing-level-spec/v1", "id": "portable-mcp",
            "scripts": [{"name": "main.lua", "source": source.name}],
            "root_script": "main.lua", "templates": [{"name": "Root", "kind": "container"}],
        })
        job = self.project / "portable.json"
        write_json(job, {"schema": 2, "level": {"spec": "level.json"}, "portable": {}})
        plan = self.root / "plan.json"
        write_json(plan, {
            "schema": 1, "domain": "genshin-qianxing-ugc", "kind": "delivery",
            "goal": "Deliver a portable level",
            "requirements": [{"id": "level", "acceptance": "Level delivered"}],
            "steps": [{
                "id": "prepare", "phase": "inspect", "owner": "miliastra-gil",
                "requirements": ["level"],
            }],
        })
        node = Path(shutil.which("node")).resolve()

        async def run():
            async with Client(self.server) as client:
                delivery = await self.call(client, "produce", {
                    "spec": job.name, "sha256": sha_file(job), "output": "portable", "summary": True,
                })
                output = Path(delivery["output"])
                self.assertEqual(output, self.outputs / "portable")
                snapshot = read_json(output / "portable/portable.json")
                self.assertTrue(snapshot["backends"]["node"]["available"])
                self.assertEqual(snapshot["backends"]["node"]["executable"], sha_file(node))
                manifest = output / "manifest.json"
                digest = delivery["outputs_sha256"]["manifest.json"]
                self.assertEqual(digest, sha_file(manifest))
                self.assertEqual(
                    delivery["outputs_sha256"]["production-report.json"],
                    sha_file(output / "production-report.json"),
                )
                inputs = {"input": str(manifest), "sha256": digest, "portable": True}
                source.rename(source.with_name("original-client.lua"))
                for report in (manifest, output / "production-report.json"):
                    result = check(plan, report)
                    self.assertEqual(result["production_evidence"]["portable_inputs"]["status"], "passed")
                inspected = (await self.call(client, "verify", inputs))["result"]
                self.assertEqual(inspected["source_check"], "packaged_inputs")
                rebuilt = (await self.call(client, "verify", {
                    **inputs, "rebuild": True,
                    "trusted_inputs_sha256": inspected["trusted_inputs_sha256"],
                }))["result"]
                self.assertEqual(rebuilt["rebuild"], "passed")
                self.assertEqual(rebuilt["portable_execution"]["status"], "passed")
                self.assertEqual(rebuilt["rebuild_differences"], [])
                self.assertGreater(rebuilt["rebuild_artifacts"], 0)
                self.assertEqual(sha_file(manifest), digest)

        asyncio.run(run())

    def test_experiment_observations_can_be_compared_with_reported_checksums(self):
        baseline = self.project / "baseline.lua"
        baseline.write_text("function Observe(seed, policy) Score = seed + policy end\n", encoding="utf-8")
        candidate = self.project / "candidate.lua"
        candidate.write_text(
            "function Observe(seed, policy)\n"
            "    if seed == 3 then error('observation unavailable') end\n"
            "    Score = seed + policy + 1\n"
            "end\n",
            encoding="utf-8",
        )
        sample = {
            "schema": 2, "entry": "Observe", "development_seeds": [2, 3],
            "holdout_seeds": [8], "split": "development", "policies": [1], "metrics": ["Score"],
        }

        async def run():
            async with Client(self.server) as client:
                observations = []
                for source, status in ((baseline, "passed"), (candidate, "failed")):
                    spec = source.with_suffix(".json")
                    write_json(spec, {**sample, "source": source.name})
                    result = await self.call(client, "experiment_run", {
                        "spec": spec.name, "sha256": sha_file(spec), "output": source.stem,
                    }, status)
                    output = Path(result["output"])
                    self.assertEqual(output, self.outputs / source.stem)
                    report = output / "observations.json"
                    digest = result["outputs_sha256"]["observations.json"]
                    self.assertEqual(digest, sha_file(report))
                    self.assertEqual(result["outputs_sha256"]["manifest.json"], sha_file(output / "manifest.json"))
                    observations.append((str(report), digest))

                (before, before_sha256), (after, after_sha256) = observations
                compared = (await self.call(client, "experiment_compare", {
                    "input": before, "sha256": before_sha256, "other": after, "other_sha256": after_sha256,
                }))["result"]
                success, failure = compared["rows"]
                self.assertEqual(success["numeric_deltas"], {"Score": 1})
                self.assertTrue(failure["before"]["passed"])
                self.assertFalse(failure["after"]["passed"])
                self.assertIn("observation unavailable", failure["after"]["error"])

        asyncio.run(run())

    def test_joint_simulation_returns_checksums_for_verification(self):
        source = self.project / "score.lua"
        source.write_text("function UpdateScore(value) Score = value end\n", encoding="utf-8")
        spec = self.project / "scenario.json"
        write_json(spec, {
            "schema": 2,
            "clients": [{"id": 1, "source": source.name}],
            "steps": [{"op": "invoke", "client": 1, "name": "UpdateScore", "args": [5]}],
            "assertions": [{"client": 1, "path": "Score", "equals": 5}],
        })

        async def run():
            async with Client(self.server) as client:
                result = await self.call(client, "simulate", {
                    "spec": spec.name, "sha256": sha_file(spec), "output": "simulation",
                })
                output = Path(result["output"])
                self.assertEqual(result["outputs_sha256"]["simulation.json"], sha_file(output / "simulation.json"))
                checked = await self.call(client, "verify", {
                    "input": str(output / "manifest.json"), "sha256": result["outputs_sha256"]["manifest.json"],
                })
                self.assertEqual(checked["result"]["source_check"], "passed")
                self.assertEqual(checked["result"]["artifact_check"], "passed")

        asyncio.run(run())

    def test_fit_mount_uses_the_same_lua_for_beyond(self):
        sample = PLUGIN / 'samples/creator-demos/png'
        source = self.project / 'checkpoint-marker.png'
        spec = self.project / 'fit.json'
        for target in (source, spec):
            shutil.copyfile(sample / target.name, target)
        source_digest = sha_file(source)
        archive = os.environ.get('MILIASTRA_TEST_BEYOND_ARCHIVE')
        if archive:
            from beyond_native import extract_native_archive, read_native_lock

            self.server.env = self.workspace_environment()
            lock = read_native_lock(PLUGIN / 'vendor/beyond')
            cache = Path(self.server.env['MILIASTRA_WONDERLAND_PLUGIN_DATA']) / 'beyond-native'
            cache.mkdir(parents=True)
            extract_native_archive(lock, Path(archive), cache / lock['sha256'])

        async def run():
            async with Client(self.server) as client:
                response = await self.call(client, 'asset_fit', {
                    'input': source.name, 'spec': spec.name, 'output': 'fit',
                })
                output = Path(response['output'])
                layer, = response['result']['layers']
                count = layer['controls']
                self.assertGreater(count, 0)
                self.assertLessEqual(count, 20)
                self.assertEqual(layer['refinement']['spill_pixels'], 0)
                self.assertTrue(layer['refinement']['worst_regions'])
                self.assertEqual(response['inputs_sha256']['input'], source_digest)
                mounted = output / 'mounted.lua'
                mounted_sha256 = sha_file(mounted)
                preview_spec = output / 'beyond.json'
                self.assertEqual(read_json(preview_spec)['scripts'][0]['sha256'], mounted_sha256)
                self.assertEqual(response['outputs_sha256']['mounted.lua'], mounted_sha256)
                self.assertEqual(response['outputs_sha256']['beyond.json'], sha_file(preview_spec))
                code = mounted.read_text(encoding='utf-8')
                self.assertIn('function OnStart()', code)
                self.assertIn((output / 'image/data.lua').read_text(encoding='utf-8').strip(), code)
                LuaRuntime().compile(code)
                if archive:
                    outcome = await client.call_tool('simulate', {
                        'spec': str(preview_spec), 'sha256': sha_file(preview_spec),
                        'output': 'preview', 'preview': True,
                    })
                    self.assertFalse(outcome.is_error, outcome)
                    preview = outcome.structured_content
                    self.assertEqual(preview['status'], 'passed', preview)
                    rendered = Path(preview['output'])
                    report = preview['result']
                    self.assertEqual(report['inputs'][str(mounted)], mounted_sha256)
                    self.assertEqual(report['render_layer'], 'software_preview')
                    self.assertEqual([item.type for item in outcome.content], ['text', 'image', 'text', 'text'])
                    self.assertIn('Lua 执行通过', outcome.content[2].text)
                    thumbnail, = [item for item in outcome.content if isinstance(item, types.ImageContent)]
                    self.assertEqual(thumbnail.mime_type, 'image/png')
                    digest = sha_file(rendered / 'preview.png')
                    self.assertEqual(preview['outputs_sha256']['preview.png'], digest)
                    self.assertEqual(sha(b64decode(thumbnail.data, validate=True)), digest)
                    self.assertFalse(thumbnail.data in json.dumps(preview))
                    render = read_json(rendered / 'render.json')
                    self.assertEqual(len(render['paint']), count)
                    self.assertTrue(all(row['primitive'] == 'rect' for row in render['paint']))
                    with Image.open(rendered / 'preview.png') as image, Image.open(output / 'image/preview.png') as fit:
                        x, y = image.width // 2, image.height // 2
                        actual = image.crop((x - 72, y - 72, x + 72, y + 72))
                        expected = fit.resize((144, 144), Image.Resampling.NEAREST)
                        self.assertEqual(actual.convert('RGBa').tobytes(), expected.convert('RGBa').tobytes())
                self.assertEqual(sha_file(source), source_digest)

        asyncio.run(run())

    def test_scene_preview_returns_top_and_side_images_in_order(self):
        draft = self.project / 'layout.json'
        write_json(draft, {
            'schema': 1, 'kind': 'whitebox-pivot', 'version': '7.2', 'mode': 'beyond',
            'groups': [{
                'key': 'door', 'pivot_relative': [0, .5, .25],
                'parts': [{'name': 'door panel', 'shape_id': 10009001,
                           'position_m': [5, 1, 0], 'scale': [2, 2, .25]}],
            }],
        })
        digest = sha_file(draft)

        async def run():
            async with Client(self.server) as client:
                outcome = await client.call_tool('scene_preview', {
                    'input': draft.name, 'sha256': digest, 'output': 'scene',
                })
            self.assertFalse(outcome.is_error, outcome)
            response = outcome.structured_content
            self.assertEqual(response['status'], 'passed')
            output = self.outputs / 'scene'
            self.assertEqual(Path(response['output']), output)
            self.assertEqual(response['inputs_sha256']['input'], digest)
            report = response['result']
            self.assertEqual(report, read_json(output / 'manifest.json'))
            self.assertEqual(report['views']['top']['axes'], ['X', 'Z'])
            self.assertEqual(report['views']['side']['axes'], ['X', 'Y'])
            self.assertEqual(response['outputs_sha256']['manifest.json'], sha_file(output / 'manifest.json'))
            self.assertEqual([item.type for item in outcome.content], ['text', 'image', 'text', 'image', 'text', 'text'])
            self.assertIn('俯视', outcome.content[0].text)
            self.assertIn('侧视', outcome.content[2].text)
            images = [item for item in outcome.content if isinstance(item, types.ImageContent)]
            for name, image in zip(('top.png', 'side.png'), images, strict=True):
                self.assertEqual(image.mime_type, 'image/png')
                self.assertEqual(sha(b64decode(image.data, validate=True)), report['files'][name])
                self.assertEqual(sha_file(output / name), report['files'][name])
                self.assertEqual(response['outputs_sha256'][name], report['files'][name])
                self.assertFalse(image.data in json.dumps(response))

        asyncio.run(run())

    def test_asset_preview_returns_images_and_counts(self):
        source = self.project / "练习 图标.png"
        shutil.copyfile(PLUGIN / "samples/creator-demos/png/checkpoint-marker.png", source)
        digest = sha_file(source)
        args = {"input": source.name, "output": "素材对比", "max_controls": 20}

        async def run():
            async with Client(self.server) as client:
                outcome = await client.call_tool("asset_preview", args)
                response = outcome.structured_content
                self.assertFalse(outcome.is_error, outcome)
                self.assertEqual(response["status"], "passed")
                self.assertEqual(response["inputs_sha256"]["input"], digest)
                output = self.outputs / args["output"]
                self.assertEqual(Path(response["output"]), output)
                persisted = read_json(output / "report.json")
                candidates = response["result"]["candidates"]
                self.assertEqual(candidates, persisted["candidates"])
                counts = [candidate["controls"] for candidate in candidates]
                self.assertGreater(counts[0], 20)
                self.assertTrue(any(0 < count <= 20 for count in counts[1:]))
                for candidate in candidates:
                    with Image.open(output / candidate["display_preview"]) as image:
                        image.verify()
                expected = (
                    ("原尺寸参考 · original · 155 个控件 · 超预算", "original"),
                    ("首选推荐 · grid-25 · 11 个控件 · 预算内", "grid-25"),
                    ("更省控件 · grid-12.5 · 5 个控件 · 预算内", "grid-12.5"),
                )
                self.assertEqual(response["result"]["recommendations"][0], expected[1][1])
                self.assertEqual([item.type for item in outcome.content], ["text"] + ["text", "image"] * 3)
                by_name = {candidate["name"]: candidate for candidate in candidates}
                for index, (caption, name) in enumerate(expected, start=1):
                    label, thumbnail = outcome.content[2 * index - 1:2 * index + 1]
                    self.assertEqual(label.text, caption)
                    self.assertEqual(thumbnail.mime_type, "image/png")
                    with (
                        Image.open(BytesIO(b64decode(thumbnail.data))) as image,
                        Image.open(output / by_name[name]["display_preview"]) as rendered,
                    ):
                        self.assertEqual(image.size, rendered.size)
                        self.assertEqual(image.tobytes(), rendered.tobytes())
                self.assertEqual(sha_file(source), digest)

                retry = await client.call_tool("asset_preview", args)
                self.assertTrue(retry.is_error)
                self.assertIn("Output exists", retry.content[0].text)
                self.assertIn("io.output_exists", retry.content[0].text)
                self.assertIn("换用尚不存在的输出目录", retry.content[0].text)
                self.assertEqual(read_json(output / "report.json"), persisted)
                invalid = await client.call_tool("asset_preview", {
                    "input": "entrance.gil", "output": "invalid-preview",
                })
                self.assertTrue(invalid.is_error)
                self.assertIn("asset.preview_invalid", invalid.structured_content["diagnostics"][0]["code"])
                self.assertFalse((self.outputs / "invalid-preview").exists())

        asyncio.run(run())

    def test_asset_generate_uses_reviewed_candidate_and_protects_inputs(self):
        source = self.project / "透明 检查点.png"
        shutil.copyfile(PLUGIN / "samples/creator-demos/png/checkpoint-marker.png", source)
        original = source.read_bytes()

        async def run():
            async with Client(self.server) as client:
                preview = await self.call(client, "asset_preview", {
                    "input": source.name, "output": "素材试算", "max_controls": 20,
                })
                report = Path(preview["output"]) / "report.json"
                report_digest = preview["outputs_sha256"]["report.json"]
                self.assertEqual(sha_file(report), report_digest)
                self.assertEqual(sha_file(report.with_name("manifest.json")),
                                 preview["outputs_sha256"]["manifest.json"])
                chosen = preview["result"]["recommendations"][0]
                self.assertEqual(chosen, "grid-25")
                candidate = next(row for row in preview["result"]["candidates"] if row["name"] == chosen)
                args = {
                    "input": source.name, "sha256": preview["inputs_sha256"]["input"],
                    "report": str(report), "report_sha256": report_digest,
                    "candidate": chosen, "output": "图元交付",
                }
                delivered = await client.call_tool("asset_generate", args)
                self.assertFalse(delivered.is_error, delivered)
                response = delivered.structured_content
                self.assertEqual(response["status"], "passed")
                self.assertEqual(response["result"]["controls"], candidate["controls"])
                self.assertEqual(candidate["controls"], 11)
                output = Path(response["output"])
                self.assertEqual(output, self.outputs / args["output"])
                self.assertEqual(read_json(output / "report.json")["preview_selection"],
                                 {"candidate": chosen, "preview_sha256": report_digest})
                self.assertEqual(sha_file(output / "preview.png"), sha_file(report.parent / candidate["preview"]))
                files = {"asset.json", "data.lua", "preview.png", "report.json", "manifest.json"}
                digests = response["outputs_sha256"]
                self.assertEqual(digests, {name: sha_file(output / name) for name in files})
                asset = read_json(output / "asset.json")
                self.assertEqual(len(asset["data"]["rects"]), 11)
                lua = LuaRuntime().execute((output / "data.lua").read_text(encoding="utf-8"))
                self.assertEqual((lua.maxRects, len(lua.rects)), (11, 11))
                image, = [item for item in delivered.content if item.type == "image"]
                with Image.open(BytesIO(b64decode(image.data))) as thumbnail:
                    self.assertEqual(thumbnail.size, (6, 6))
                    thumbnail.verify()

                verified_args = {
                    "input": str(output / "manifest.json"), "sha256": digests["manifest.json"], "artifacts_only": True,
                }
                verification = (await self.call(client, "verify", verified_args))["result"]
                self.assertEqual(verification["artifact_check"], "passed")
                self.assertEqual(verification["source_check"], "not_checked")
                source_verification = (await self.call(client, "verify", {
                    **verified_args, "artifacts_only": False,
                }, "failed"))["result"]
                self.assertEqual(source_verification["diagnostics"][0]["code"], "verify.artifacts_only_required")
                data_file = output / "data.lua"
                original_data = data_file.read_bytes()
                data_file.write_bytes(original_data + b"\n")
                changed = (await self.call(client, "verify", verified_args, "failed"))["result"]
                self.assertEqual(changed["artifact_changes"], ["data.lua"])
                data_file.write_bytes(original_data)

                repeat = await client.call_tool("asset_generate", args)
                self.assertTrue(repeat.is_error)
                self.assertIn("io.output_exists", repeat.content[0].text)
                self.assertEqual(digests, {name: sha_file(output / name) for name in files})
                self.assertEqual(sha_file(report), report_digest)
                self.assertEqual(source.read_bytes(), original)

                other = "grid-12.5-fewer-colors"
                self.assertNotIn(other, preview["result"]["recommendations"])
                alternative = await self.call(client, "asset_generate", {
                    **args, "candidate": other, "output": "其他候选",
                })
                self.assertEqual(alternative["result"]["controls"], 5)
                self.assertEqual(alternative["result"]["preview_selection"]["candidate"], other)

                for name, detail in (("original", "exceeds a declared constraint"),
                                     ("unknown-candidate", "Expected an exact preview candidate name")):
                    refused = await client.call_tool("asset_generate", {**args, "candidate": name, "output": name})
                    self.assertTrue(refused.is_error)
                    diagnostic, = refused.structured_content["diagnostics"]
                    self.assertEqual(diagnostic["code"], "asset.generate_invalid")
                    self.assertIn(detail, diagnostic["detail"])
                    self.assertFalse((self.outputs / name).exists())

                foreign = self.root / "report.json"
                shutil.copyfile(report, foreign)
                outside = await client.call_tool("asset_generate", {**args, "report": str(foreign), "output": "outside"})
                self.assertTrue(outside.is_error)
                self.assertIn("Path outside allowed", outside.content[0].text)
                self.assertFalse((self.outputs / "outside").exists())

                source.write_bytes(original + b"\n")
                stale_input = await client.call_tool("asset_generate", {**args, "output": "stale-input"})
                self.assertTrue(stale_input.is_error)
                self.assertIn("Input digest mismatch: input", stale_input.content[0].text)
                changed = await client.call_tool("asset_generate", {
                    **args, "sha256": sha_file(source), "output": "stale-input",
                })
                self.assertTrue(changed.is_error)
                self.assertIn("Preview source digest differs", changed.structured_content["diagnostics"][0]["detail"])
                self.assertFalse((self.outputs / "stale-input").exists())
                source.write_bytes(original)

                report.write_bytes(report.read_bytes() + b"\n")
                stale_report = await client.call_tool("asset_generate", {**args, "output": "stale-report"})
                self.assertTrue(stale_report.is_error)
                self.assertIn("Input digest mismatch: report", stale_report.content[0].text)
                self.assertFalse((self.outputs / "stale-report").exists())

        asyncio.run(run())

    def test_asset_preview_labels_original_only_once_when_it_is_recommended(self):
        source = self.project / "灰阶.png"
        with Image.new("RGBA", (8, 8)) as image:
            for index in range(64):
                shade = 4 * index
                image.putpixel((index % 8, index // 8), (shade, shade, shade, 255))
            image.save(source)

        async def run():
            async with Client(self.server) as client:
                outcome = await client.call_tool("asset_preview", {
                    "input": source.name, "output": "灰阶试算",
                })
                self.assertFalse(outcome.is_error, outcome)
                self.assertEqual(outcome.structured_content["result"]["recommendations"][0], "original")
                self.assertEqual([item.type for item in outcome.content], ["text", "text", "image", "text", "image"])
                self.assertEqual(outcome.content[1].text, "原尺寸参考／首选推荐 · original · 64 个控件 · 未设预算")
                self.assertTrue(outcome.content[3].text.startswith("更省控件 · "))

        asyncio.run(run())

    def test_asset_generate_rejects_lost_foreground_and_preserves_transparent_input(self):
        sparse = self.project / "单像素.png"
        transparent = self.project / "全透明.png"
        with Image.new("RGBA", (32, 32)) as image:
            image.save(transparent)
            image.putpixel((16, 16), (255, 0, 0, 255))
            image.save(sparse)

        async def run():
            async with Client(self.server) as client:
                source_digest = sha_file(sparse)
                sparse_preview = await self.call(client, "asset_preview", {
                    "input": sparse.name, "output": "单像素试算", "max_controls": 20,
                })
                self.assertTrue(sparse_preview["result"]["has_foreground"])
                candidate = "smaller-grid"
                row = next(row for row in sparse_preview["result"]["candidates"] if row["name"] == candidate)
                self.assertEqual(row["controls"], 0)
                self.assertTrue(row["within_budget"])
                self.assertNotIn(candidate, sparse_preview["result"]["recommendations"])
                sparse_report = Path(sparse_preview["output"]) / "report.json"
                report_digest = sparse_preview["outputs_sha256"]["report.json"]
                rejected = await client.call_tool("asset_generate", {
                    "input": sparse.name, "sha256": source_digest, "report": str(sparse_report),
                    "report_sha256": report_digest, "candidate": candidate, "output": "无效交付",
                })
                self.assertTrue(rejected.is_error)
                diagnostic, = rejected.structured_content["diagnostics"]
                self.assertEqual(diagnostic["code"], "asset.foreground_lost")
                self.assertIn("丢失全部可见内容", diagnostic["message"])
                self.assertFalse((self.outputs / "无效交付").exists())

                cli_output = self.outputs / "无效终端交付"
                cli = await asyncio.to_thread(subprocess.run, [
                    sys.executable, "-X", "utf8", "-B", str(PLUGIN / "scripts/qianxing.py"), "assets", "generate",
                    "--from-preview", str(sparse_report), "--candidate", candidate, "--out", str(cli_output),
                ], capture_output=True, encoding="utf-8", timeout=30)
                self.assertEqual(cli.returncode, 2, cli.stderr)
                self.assertEqual(json.loads(cli.stderr)["diagnostics"], [diagnostic])
                self.assertFalse(cli_output.exists())
                self.assertEqual(sha_file(sparse), source_digest)
                self.assertEqual(sha_file(sparse_report), report_digest)

                no_candidate = await client.call_tool("asset_preview", {
                    "input": sparse.name, "output": "单像素粗网格试算", "max_controls": 20, "step": 2,
                })
                self.assertFalse(no_candidate.is_error, no_candidate)
                self.assertEqual(no_candidate.structured_content["result"]["recommendations"], [])
                self.assertIn("asset_search_no_candidate", no_candidate.content[0].text)
                self.assertEqual([item.type for item in no_candidate.content], ["text", "text", "image"])
                self.assertEqual(no_candidate.content[1].text, "指定网格参考 · original · 0 个控件 · 预算内 · 未保留前景")

                blank_preview = await client.call_tool("asset_preview", {
                    "input": transparent.name, "output": "全透明试算", "max_controls": 20,
                })
                self.assertFalse(blank_preview.is_error, blank_preview)
                preview = blank_preview.structured_content
                self.assertFalse(preview["result"]["has_foreground"])
                self.assertTrue(all("全透明" in item.text for item in blank_preview.content[1::2]))
                blank = await client.call_tool("asset_generate", {
                    "input": transparent.name, "sha256": preview["inputs_sha256"]["input"],
                    "report": str(Path(preview["output"]) / "report.json"),
                    "report_sha256": preview["outputs_sha256"]["report.json"],
                    "candidate": preview["result"]["recommendations"][0], "output": "全透明交付",
                })
                self.assertFalse(blank.is_error, blank)
                self.assertIn("0 个控件 · 预算内 · 全透明", blank.content[1].text)
                self.assertEqual(blank.structured_content["result"]["controls"], 0)
                self.assertFalse(blank.structured_content["result"]["has_foreground"])
                data = self.outputs / "全透明交付" / "data.lua"
                lua = LuaRuntime().execute(data.read_text(encoding="utf-8"))
                self.assertEqual((lua.maxRects, len(lua.palette), len(lua.rects)), (0, 0, 0))

        asyncio.run(run())

    def test_common_failures_include_recovery_and_original_details(self):
        async def run():
            unbound = StdioServerParameters(command=sys.executable, args=self.server.args[:-4],
                                           env=self.workspace_environment())
            async with Client(unbound) as client:
                denied = await client.call_tool("project_inspect", {"input": "entrance.gil"})
                self.assertTrue(denied.is_error)
                self.assertIn("mcp.workspace_required", denied.content[0].text)
                self.assertIn("尚未绑定工程目录", denied.content[0].text)
                self.assertIn("MILIASTRA_WONDERLAND_PROJECT_ROOT", denied.content[0].text)
                self.assertIn("Open a workspace", denied.content[0].text)

                version = await self.call(client, "docs_search", {"version": "1.0.0", "query": "节点"}, "failed")
                diagnostic, = version["result"]["diagnostics"]
                self.assertEqual(diagnostic["code"], "platform.version_unknown")
                self.assertIn("核对游戏内版本", diagnostic["message"])
                self.assertIn("7.2", diagnostic["supported_versions"])
                self.assertEqual(diagnostic["detail"], "Unknown platform version: 1.0.0")

            async with Client(self.server) as client:
                absent = await client.call_tool("project_inspect", {"input": "缺失 关卡.gil"})
                self.assertTrue(absent.is_error)
                self.assertIn("io.input_missing", absent.content[0].text)
                self.assertIn("缺失 关卡.gil", absent.content[0].text)
                self.assertIn("请核对文件名、扩展名", absent.content[0].text)
                self.assertIn("Input file missing", absent.content[0].text)
                outside = await client.call_tool("project_inspect", {"input": "../other.gil"})
                self.assertTrue(outside.is_error)
                self.assertIn("io.outside_allowed_roots", outside.content[0].text)
                self.assertIn("从已授权目录选择", outside.content[0].text)
                self.assertIn("Path outside allowed project/output roots", outside.content[0].text)
                changed = await client.call_tool("project_inspect", {
                    "input": "entrance.gil", "sha256": "0" * 64,
                })
                self.assertTrue(changed.is_error)
                self.assertIn("mcp.input_sha256_mismatch", changed.content[0].text)
                self.assertIn("SHA-256 校验值不一致", changed.content[0].text)
                self.assertIn("Input digest mismatch: input", changed.content[0].text)

        asyncio.run(run())

    @unittest.skipUnless(sys.platform == "win32" and shutil.which("node"), "Windows Node.js required")
    def test_junction_diagnostic_keeps_the_link_component(self):
        child = self.project / "actual"
        child.mkdir()
        (child / "entrance.gil").write_bytes(self.raw)
        project_link = self.root / "Documents"
        output_link = self.root / "Output link"
        child_link = self.project / "子目录联接"
        for link, target in (
            (project_link, self.project), (output_link, self.outputs), (child_link, child),
        ):
            subprocess.run([
                "node", "-e", "require('node:fs').symlinkSync(process.argv[1], process.argv[2], 'junction')",
                str(target), str(link),
            ], check=True, capture_output=True, timeout=10)
            self.addCleanup(link.rmdir)

        async def check_link(client, tool, args, link):
            outcome = await client.call_tool(tool, args)
            self.assertTrue(outcome.is_error, outcome)
            message = outcome.content[0].text
            problem, = json.loads(message[message.index("{"):])["diagnostics"]
            self.assertEqual(problem["code"], "io.linked_path")
            self.assertEqual(Path(problem["source"]), link)
            self.assertIn("目录联接", problem["message"])
            self.assertIn("文件夹的实际位置", problem["message"])
            self.assertIn("Linked", problem["detail"])

        async def run():
            for project, output, tool, args, link in (
                (project_link / "actual", self.outputs, "project_inspect", {"input": "entrance.gil"}, project_link),
                (self.project, output_link, "asset_preview", {"input": "entrance.gil", "output": "review"}, output_link),
                (self.project, self.outputs, "project_inspect", {"input": "子目录联接/entrance.gil"}, child_link),
            ):
                server = StdioServerParameters(
                    command=sys.executable,
                    args=[*self.server.args[:-4], "--project", str(project), "--output-root", str(output)],
                    env=self.workspace_environment(),
                )
                async with Client(server) as client:
                    await check_link(client, tool, args, link)

            roots = [project_link / "actual"]

            async def list_roots(_):
                return types.ListRootsResult(roots=[types.Root(uri=path.as_uri()) for path in roots])

            server = StdioServerParameters(command=sys.executable, args=self.server.args[:-4],
                                           env=self.workspace_environment())
            async with Client(server, list_roots_callback=list_roots, mode="legacy") as client:
                await check_link(client, "project_inspect", {"input": "entrance.gil"}, project_link)
                roots.append(self.project)
                result = await self.call(client, "project_inspect", {"input": "entrance.gil"})
                self.assertEqual(result["inputs_sha256"]["input"], sha(self.raw))

        asyncio.run(run())

    def test_timeout_points_to_the_matching_setting(self):
        from miliastra.mcp.bridge import Bridge

        async def run():
            bridge = Bridge()
            with patch.object(bridge, "_call", side_effect=TimeoutError):
                for tool, variable in (
                    ("docs_search", "MILIASTRA_WONDERLAND_MCP_TIMEOUT_SECONDS"),
                    ("graph_build", "MILIASTRA_WONDERLAND_MCP_BUILD_TIMEOUT_SECONDS"),
                ):
                    result = await bridge.call(tool, {})
                    self.assertEqual(result["status"], "failed")
                    problem, = result["diagnostics"]
                    self.assertEqual(problem["code"], "mcp.timeout")
                    self.assertIn("任务超过插件设定", problem["message"])
                    self.assertIn(variable, problem["message"])
                    self.assertEqual(problem["detail"], "MCP operation exceeded its total timeout")

        asyncio.run(run())

    def test_graph_compiles_with_default_output_and_continues_into_reviewed_gil_edit(self):
        from ayaya_bridge import RUNTIME
        from level_inventory import inspect_file
        from miliastra.mcp.workspace import workspace_outputs

        data = self.root / "plugin data" / ("a" * 40)
        compiler_temp = self.root / "t"
        compiler_temp.mkdir()
        output_root = workspace_outputs(data, self.project.resolve())
        server = StdioServerParameters(
            command=self.server.command, args=self.server.args[:-2],
            env={
                **self.workspace_environment(),
                "MILIASTRA_WONDERLAND_PLUGIN_DATA": str(data),
                "TEMP": str(compiler_temp), "TMP": str(compiler_temp), "TMPDIR": str(compiler_temp),
            },
        )
        template = (RUNTIME / "assets/gil-templates/server"
                    / "autowire_templates_test2_server_direct_export_v2.gil")
        template_digest = sha_file(template)
        source = self.project / 'graph.py'
        source.write_text(
            '"""\ngraph_id: server_mcp_delivery_test\ngraph_name: EntryLog\ngraph_type: server\n"""\n'
            'from app.runtime.engine.graph_prelude_server import *\n'
            'class EntryLog:\n'
            '    def __init__(self, game, owner_entity):\n'
            '        self.game = game\n'
            '        self.owner_entity = owner_entity\n'
            '    def on_实体创建时(self, 事件源实体, 事件源GUID):\n'
            '        打印字符串(self.game, 字符串="ready")\n'
            '    def register_handlers(self):\n'
            '        return\n',
            encoding='utf-8',
        )
        job = {"schema": 1, "graphs": [{"source": source.name}], "formats": ["gia"]}
        write_json(self.project / "build.json", job)
        write_json(self.project / "gil-build.json", {**job, "formats": ["gia", "gil"]})
        invalid = self.project / "invalid.py"
        invalid.write_text(source.read_text(encoding="utf-8").replace("打印字符串", "不存在的节点"), encoding="utf-8")
        write_json(self.project / "invalid-build.json", {**job, "graphs": [{"source": invalid.name}]})

        async def run():
            async with Client(server) as client:
                rejected = await self.call(client, "graph_build", {
                    "spec": "gil-build.json", "output": "blocked",
                }, "failed")
                self.assertIsNone(rejected["output"])
                failed = await self.call(client, "graph_build", {
                    "spec": "invalid-build.json", "output": "invalid",
                }, "failed")
                self.assertIn("validate-0 failed", failed["error"])
                self.assertIsNone(failed["output"])
                self.assertEqual(list(output_root.iterdir()), [])
                self.assertEqual(list(compiler_temp.iterdir()), [])
                compiled = await self.call(client, "graph_build", {
                    "spec": "build.json", "output": "compiled",
                })
                gia, = compiled["result"]["gia"]
                self.assertEqual(Path(compiled["output"]), output_root / "compiled")
                compiled_file = output_root / "compiled" / gia
                self.assertEqual(sha_file(compiled_file), compiled["outputs_sha256"][gia])
                self.assertEqual(compiled["inputs_sha256"]["spec"], sha_file(self.project / "build.json"))

                export_log = (compiled_file.parent.parent / "logs/gia-export.txt").read_text(encoding="utf-8")
                log_prefix = "- output_dir: "
                compiler_output, = (Path(line.removeprefix(log_prefix)) for line in export_log.splitlines()
                                    if line.startswith(log_prefix))
                self.assertTrue(compiler_output.is_relative_to(compiler_temp.resolve()))
                self.assertEqual(list(compiler_temp.iterdir()), [])
                self.assertEqual(list(output_root.iterdir()), [output_root / "compiled"])

                base = {"input": "entrance.gil", "sha256": sha_file(self.project / "entrance.gil")}
                plan = await self.call(client, "native_plan", {
                    **base, "output": "review",
                    "patch": {
                        "schema": 2, "allowed_top_level_fields": [10],
                        "operations": [{"op": "append_graph", "source": str(compiled_file)}],
                    },
                })
                applied = await self.call(client, "native_apply", {
                    **base, "output": "updated", "plan": str(Path(plan["output"]) / "plan.json"),
                    "plan_sha256": plan["outputs_sha256"]["plan.json"],
                })
                exported = Path(applied["output"]) / "level.gil"
                inventory = inspect_file(exported)
                self.assertIn("EntryLog", {graph["name"] for graph in inventory["graphs"]})
                self.assertEqual(sha_file(exported), applied["outputs_sha256"]["level.gil"])
                self.assertEqual((self.project / "entrance.gil").read_bytes(), self.raw)
                self.assertEqual(sha_file(template), template_digest)

        asyncio.run(run())

    def test_trace_preview_write_and_verify(self):
        async def run():
            async with Client(self.server) as client:
                inp = {"input": "entrance.gil"}
                full = await self.call(client, "project_inspect", inp)
                selected = await self.call(client, "project_inspect", {
                    **inp, "selector": {"kind": "entity", "id": INSTANCE},
                })
                self.assertIn("objects", full["result"])
                self.assertEqual(selected["result"]["target"]["id"], INSTANCE)
                self.assertIn(TEMPLATE, [item["id"] for item in selected["result"]["dependencies"]])
                missing = await self.call(client, "project_inspect", {
                    **inp, "selector": {"kind": "custom_variable", "name": "missing"},
                }, "failed")
                diagnostic, = missing["result"]["diagnostics"]
                self.assertEqual(diagnostic["code"], "project.selector_missing")
                self.assertEqual(diagnostic["candidates"], [])
                traced = await self.call(client, "project_inspect", {
                    **inp, "selector": {"kind": "custom_variable", "name": VARIABLE}, "transitive": True,
                })
                self.assertIn("inherits_custom_variable", {edge["relation"] for edge in traced["result"]["references"]})

                bound = {**inp, "sha256": selected["inputs_sha256"]["input"]}
                patch = {
                    "schema": 2, "base_sha256": bound["sha256"], "allowed_top_level_fields": [4],
                    "operations": [
                        {"op": "set_custom_variable_default", "section": 4, "entity_id": TEMPLATE,
                         "name": VARIABLE, "value": 12},
                    ],
                }
                malformed = await self.call(client, "native_plan", {
                    **bound, "patch": {**patch, "operations": {}}, "output": "invalid-review",
                }, "failed")
                self.assertIn("operations as a list of objects", malformed["error"])
                self.assertFalse((self.outputs / "invalid-review").exists())
                wrong_base = await client.call_tool("native_plan", {
                    **bound, "patch": {**patch, "base_sha256": "0" * 64}, "output": "wrong-base",
                })
                self.assertTrue(wrong_base.is_error, wrong_base)
                self.assertIn("native.base_sha256_mismatch", wrong_base.content[0].text)
                self.assertFalse((self.outputs / "wrong-base").exists())
                inline = {k: v for k, v in patch.items() if k != "base_sha256"}
                planned = await self.call(client, "native_plan", {**bound, "patch": inline, "output": "review"})
                self.assertEqual(planned["result"]["patch"]["base_sha256"], bound["sha256"])
                self.assertTrue(planned["result"]["difference"]["protected"]["unchanged"])
                self.assertFalse((self.outputs / "review/level.gil").exists())
                plan = Path(planned["output"]) / "plan.json"
                self.assertEqual(sha_file(plan), planned["outputs_sha256"]["plan.json"])

                apply = {**bound, "plan": str(plan), "plan_sha256": planned["outputs_sha256"]["plan.json"],
                         "output": "edited"}
                wrong_hash = await client.call_tool("native_apply", {**apply, "plan_sha256": "0" * 64})
                self.assertTrue(wrong_hash.is_error, wrong_hash)
                self.assertIn("Input digest mismatch: plan", wrong_hash.content[0].text)
                self.assertFalse((self.outputs / "edited").exists())
                edited = await self.call(client, "native_apply", apply)
                detail, = edited["result"]["operations"]
                self.assertEqual((detail["before"], detail["after"]), (7, 12))
                output = Path(edited["output"]) / "level.gil"
                self.assertEqual(sha_file(output), edited["outputs_sha256"]["level.gil"])
                self.assertEqual(sha_file(output), planned["result"]["result_sha256"])

                diff_args = {**bound, "other": str(output), "other_sha256": edited["outputs_sha256"]["level.gil"]}
                diff = await self.call(client, "native_diff", {**diff_args, "allowed_top_level_fields": [4]})
                self.assertTrue(diff["result"]["protected"]["unchanged"])
                denied = await self.call(client, "native_diff", {**diff_args, "allowed_top_level_fields": []}, "failed")
                self.assertFalse(denied["result"]["protected"]["unchanged"])
                manifest = Path(edited["output"]) / "manifest.json"
                verified = await self.call(client, "verify", {
                    "input": str(manifest), "sha256": edited["outputs_sha256"]["manifest.json"],
                    "rebuild": False, "portable": False,
                })
                self.assertEqual(verified["result"]["editor"], "not_checked")
                self.assertEqual((self.project / "entrance.gil").read_bytes(), self.raw)

                # The original file-based plan can still bind external section data.
                reference = self.project / "reference.gil"
                reference.write_bytes(output.read_bytes())
                spec = self.project / "patch.json"
                write_json(spec, {**patch, "operations": [{"op": "section_from", "field": 4, "source": reference.name}]})
                file_plan_args = {**bound, "spec": spec.name, "spec_sha256": sha_file(spec), "output": "file-review"}
                invalid = await client.call_tool("native_plan", {**file_plan_args, "patch": patch})
                self.assertTrue(invalid.is_error, invalid)
                self.assertIn("Provide patch, or provide spec with spec_sha256", invalid.content[0].text)
                file_plan = await self.call(client, "native_plan", file_plan_args)
                file_apply = await self.call(client, "native_apply", {
                    **bound, "plan": str(Path(file_plan["output"]) / "plan.json"),
                    "plan_sha256": file_plan["outputs_sha256"]["plan.json"], "output": "file-edit",
                })
                self.assertEqual(file_apply["outputs_sha256"]["level.gil"], edited["outputs_sha256"]["level.gil"])
                reference.write_bytes(self.raw)
                for delivery in (file_plan, file_apply):
                    stale = await self.call(client, "verify", {
                        "input": str(Path(delivery["output"]) / "manifest.json"),
                        "sha256": delivery["outputs_sha256"]["manifest.json"],
                        "rebuild": False, "portable": False,
                    }, "failed")
                    self.assertEqual(stale["result"]["source_changes"], [str(reference)])

        asyncio.run(run())

    def test_session_roots_switch_and_scope_default_output(self):
        another = self.root / "另一关卡"
        another.mkdir()
        (another / "entrance.gil").write_bytes(initial_level("Second", (2, 2)))
        roots = [self.project]

        async def list_roots(_):
            return types.ListRootsResult(roots=[types.Root(uri=directory.as_uri()) for directory in roots])

        async def run():
            params = StdioServerParameters(command=sys.executable,
                                           args=self.server.args[:-4], env=self.workspace_environment())
            async with Client(params, list_roots_callback=list_roots, mode="legacy") as client:
                original = await self.call(client, "project_inspect", {"input": "entrance.gil", "scope": "scene"})
                self.assertFalse((self.root / "plugin-data").exists())
                context = (await self.call(client, "doctor", {}))["result"]["project_context"]
                self.assertEqual((context["source"], context["output_source"]), ("mcp_roots", "plugin_data"))
                plan = await self.call(client, "native_plan", {
                    "input": "entrance.gil", "sha256": original["inputs_sha256"]["input"], "output": "review",
                    "patch": {"schema": 2, "allowed_top_level_fields": [4],
                              "operations": [{"op": "set_custom_variable_default", "section": 4,
                                              "entity_id": TEMPLATE, "name": VARIABLE, "value": 12}]},
                })
                self.assertEqual(Path(plan["output"]).parent, Path(context["output_root"]))
                self.assertTrue((Path(plan["output"]) / "plan.json").is_file())
                roots[:] = [another]
                switched = await self.call(client, "project_inspect", {"input": "entrance.gil", "scope": "scene"})
                self.assertEqual(switched["inputs_sha256"]["input"], sha_file(another / "entrance.gil"))
                for escaped in (str(self.project / "entrance.gil"), str(Path(plan["output"]) / "plan.json"),
                                "../project/entrance.gil"):
                    denied = await client.call_tool("project_inspect", {"input": escaped})
                    self.assertTrue(denied.is_error, denied)
                    self.assertIn("outside allowed", denied.content[0].text)

                roots[:] = [self.project, another]
                denied = await client.call_tool("project_inspect", {"input": "entrance.gil"})
                self.assertTrue(denied.is_error, denied)
                self.assertIn("mcp.workspace_ambiguous", denied.content[0].text)
                selected = await self.call(client, "project_inspect", {
                    "input": str(self.project / "entrance.gil"), "scope": "scene",
                })
                self.assertEqual(selected["inputs_sha256"], original["inputs_sha256"])
                forbidden = await client.call_tool("native_diff", {
                    "input": str(self.project / "entrance.gil"), "other": str(another / "entrance.gil"),
                })
                self.assertTrue(forbidden.is_error, forbidden)

        asyncio.run(run())

    def test_unsupported_session_roots_preserve_runtime_config_results(self):
        async def unsupported_roots(_):
            return types.ErrorData(code=types.METHOD_NOT_FOUND, message="Roots unavailable")

        config = self.root / "runtime.json"
        write_json(config, {"schema": 1, "python": sys.executable,
                            "project_root": str(self.project), "output_root": str(self.outputs)})
        env = {**self.workspace_environment(), "MILIASTRA_WONDERLAND_RUNTIME_CONFIG": str(config)}

        async def run():
            params = StdioServerParameters(command=sys.executable, args=self.server.args[:-4], env=env)
            async with Client(params, list_roots_callback=unsupported_roots, mode="legacy") as client:
                context = (await self.call(client, "doctor", {}))["result"]["project_context"]
                self.assertEqual(context["source"], "runtime_config")
                self.assertIn("Roots unavailable", context["roots_error"])
                original = await self.call(client, "project_inspect", {"input": "entrance.gil", "scope": "scene"})
                plan = await self.call(client, "native_plan", {
                    "input": "entrance.gil", "sha256": original["inputs_sha256"]["input"], "output": "review",
                    "patch": {"schema": 2, "allowed_top_level_fields": [4],
                              "operations": [{"op": "set_custom_variable_default", "section": 4,
                                              "entity_id": TEMPLATE, "name": VARIABLE, "value": 12}]},
                })
                self.assertEqual(Path(plan["output"]), self.outputs / "review")
                self.assertEqual(sha_file(self.outputs / "review/plan.json"), plan["outputs_sha256"]["plan.json"])

        asyncio.run(run())

    @unittest.skipUnless(sys.platform == "win32" and shutil.which("node"), "Windows Node.js required")
    def test_launcher_reads_updated_runtime_workspace_without_restart(self):
        second = self.root / "second"
        second.mkdir()
        (second / "entrance.gil").write_bytes(initial_level("Changed", (2, 2)))
        config = self.root / "runtime.json"
        env = {**self.workspace_environment(), "MILIASTRA_WONDERLAND_RUNTIME_CONFIG": str(config)}
        binding = {"schema": 1, "python": sys.executable}
        write_json(config, {**binding, "project_root": str(self.project)})

        async def run():
            params = StdioServerParameters(command="node", args=[str(PLUGIN / "scripts/mcp_launcher.cjs")], env=env)
            async with Client(params) as client:
                context = (await self.call(client, "doctor", {}))["result"]["project_context"]
                self.assertEqual((context["source"], context["project_root"]), ("runtime_config", str(self.project)))
                write_json(config, {**binding, "project_root": str(second), "output_root": str(second / "invalid")})
                result = await self.call(client, "project_inspect", {"input": "entrance.gil", "scope": "scene"})
                self.assertEqual(result["inputs_sha256"]["input"], sha_file(second / "entrance.gil"))
                context = (await self.call(client, "doctor", {}))["result"]["project_context"]
                self.assertEqual(context["missing"], ["output_root"])
                self.assertEqual(context["project_root"], str(second))

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
