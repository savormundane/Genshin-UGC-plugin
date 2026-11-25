"""Public fixture for a reviewed template edit over the real MCP stdio transport."""

import asyncio
from base64 import b64decode
from io import BytesIO
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from mcp import Client, StdioServerParameters, types
from PIL import Image

from authoring_io import PLUGIN, read_json, sha_file, write_json
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

    def test_asset_preview_returns_images_and_counts(self):
        source = self.project / "练习 图标.png"
        with Image.new("RGBA", (16, 16)) as image:
            for y in range(1, 15):
                for x in range(1, 15):
                    image.putpixel((x, y), (255, 48, 64, 255) if (x + y) % 2 else (0, 80, 255, 255))
            image.save(source)
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
                thumbnails = [item for item in outcome.content if item.type == "image"]
                self.assertEqual(len(thumbnails), 2)
                for thumbnail in thumbnails:
                    self.assertEqual(thumbnail.mime_type, "image/png")
                    with Image.open(BytesIO(b64decode(thumbnail.data))) as image:
                        image.verify()
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
                image, = [item for item in delivered.content if item.type == "image"]
                with Image.open(BytesIO(b64decode(image.data))) as thumbnail:
                    self.assertEqual(thumbnail.size, (6, 6))
                    thumbnail.verify()

                repeat = await client.call_tool("asset_generate", args)
                self.assertTrue(repeat.is_error)
                self.assertIn("io.output_exists", repeat.content[0].text)
                self.assertEqual(digests, {name: sha_file(output / name) for name in files})
                self.assertEqual(sha_file(report), report_digest)
                self.assertEqual(source.read_bytes(), original)

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
