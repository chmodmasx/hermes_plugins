from __future__ import annotations

import importlib.util
import inspect
import json
import socket
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


def load_plugin():
    name = "gitea_hermes_testpkg"
    for key in list(sys.modules):
        if key == name or key.startswith(name + "."):
            sys.modules.pop(key, None)
    spec = importlib.util.spec_from_file_location(name, PLUGIN / "__init__.py", submodule_search_locations=[str(PLUGIN)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class FakeContext:
    def __init__(self):
        self.tools = {}
    def register_tool(self, *, name, toolset=None, schema=None, handler=None, **kwargs):
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler, **kwargs}


def manifest_tools():
    lines = (PLUGIN / "plugin.yaml").read_text().splitlines()
    out = []
    in_tools = False
    for line in lines:
        if line == "provides_tools:":
            in_tools = True
            continue
        if in_tools and line.startswith("  - "):
            out.append(line[4:].strip())
            continue
        if in_tools and line and not line.startswith(" "):
            break
    return out


class PluginContractTests(unittest.TestCase):
    def test_manifest_is_v1_conservative(self):
        text = (PLUGIN / "plugin.yaml").read_text()
        self.assertNotIn("manifest_version:", text)
        self.assertNotIn("python_dependencies:", text)
        self.assertNotIn("config_schema:", text)

    def test_declared_registered_and_schema_tools_match(self):
        mod = load_plugin()
        ctx = FakeContext()
        mod.register(ctx)
        declared = set(manifest_tools())
        self.assertEqual(declared, set(mod.SCHEMAS))
        self.assertEqual(declared, set(ctx.tools))
        self.assertEqual(declared, set(mod.HANDLERS))
        self.assertEqual(33, len(declared))

    def test_register_performs_no_network(self):
        mod = load_plugin()
        ctx = FakeContext()
        original = socket.socket
        def blocked(*args, **kwargs):
            raise AssertionError("network attempted during register(ctx)")
        socket.socket = blocked
        try:
            mod.register(ctx)
        finally:
            socket.socket = original
        self.assertEqual(33, len(ctx.tools))

    def test_all_handlers_accept_kwargs_and_return_json_errors(self):
        mod = load_plugin()
        for name, handler in mod.HANDLERS.items():
            sig = inspect.signature(handler)
            self.assertTrue(any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()), name)
            raw = handler({}, future_context="ok")
            parsed = json.loads(raw)
            self.assertIsInstance(parsed, dict, name)
            self.assertIn("ok", parsed, name)

    def test_gitea_127_review_event_enum(self):
        mod = load_plugin()
        enum = mod.SCHEMAS["gitea_pr_review"]["parameters"]["properties"]["event"]["enum"]
        self.assertEqual(["APPROVED", "REQUEST_CHANGES", "COMMENT"], enum)
        self.assertNotIn("APPROVE", enum)

    def test_issue_update_matches_gitea_127_edit_issue_option(self):
        mod = load_plugin()
        props = mod.SCHEMAS["gitea_issue_update"]["parameters"]["properties"]
        self.assertNotIn("labels", props)
        self.assertTrue({"title", "body", "state", "assignees", "milestone"}.issubset(props))

    def test_toolsets_are_read_or_write(self):
        mod = load_plugin(); ctx = FakeContext(); mod.register(ctx)
        self.assertEqual({"gitea_read", "gitea_write"}, {v["toolset"] for v in ctx.tools.values()})
        for name in mod.WRITE_TOOLS:
            self.assertEqual("gitea_write", ctx.tools[name]["toolset"])
        for name in mod.READ_TOOLS:
            self.assertEqual("gitea_read", ctx.tools[name]["toolset"])

    def test_gitea_127_actions_schema_contract(self):
        mod = load_plugin()
        runs = mod.SCHEMAS["gitea_actions_runs"]["parameters"]["properties"]
        self.assertTrue({"actor", "head_sha", "exclude_pull_requests", "workflow_id"}.issubset(runs))
        jobs = mod.SCHEMAS["gitea_actions_jobs"]["parameters"]["properties"]
        self.assertTrue({"status", "page", "limit", "sort", "order"}.issubset(jobs))
        artifacts = mod.SCHEMAS["gitea_actions_artifacts"]["parameters"]["properties"]
        self.assertIn("name", artifacts)
        runners = mod.SCHEMAS["gitea_runners_list"]["parameters"]["properties"]
        self.assertEqual({"owner", "repo", "disabled"}, set(runners))


if __name__ == "__main__":
    unittest.main()
