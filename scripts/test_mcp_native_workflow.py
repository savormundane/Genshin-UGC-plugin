"""Public fixture for a reviewed template edit over the real MCP stdio transport."""

import asyncio
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import Client, StdioServerParameters

from authoring_io import PLUGIN, sha_file, write_json
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

    async def call(self, client, tool, params, status="passed"):
        outcome = await client.call_tool(tool, params)
        self.assertFalse(outcome.is_error, outcome)
        self.assertEqual(outcome.structured_content["status"], status, outcome)
        return outcome.structured_content

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
                planned = await self.call(client, "native_plan", {**bound, "patch": patch, "output": "review"})
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


if __name__ == "__main__":
    unittest.main()
