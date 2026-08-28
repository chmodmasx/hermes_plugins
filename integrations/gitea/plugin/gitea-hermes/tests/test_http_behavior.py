from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


def load_plugin():
    name = "gitea_hermes_http_testpkg"
    for key in list(sys.modules):
        if key == name or key.startswith(name + "."):
            sys.modules.pop(key, None)
    spec = importlib.util.spec_from_file_location(name, PLUGIN / "__init__.py", submodule_search_locations=[str(PLUGIN)])
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    assert spec.loader; spec.loader.exec_module(module)
    return module


class Handler(BaseHTTPRequestHandler):
    posts = 0
    auth_headers = []
    requests = []
    def log_message(self, *args):
        pass
    def _send(self, status, body, ctype="application/json", headers=None):
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        Handler.auth_headers.append(self.headers.get("Authorization"))
        parsed = urlsplit(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        Handler.requests.append((path, query))
        if path == "/api/v1/version": return self._send(200, {"version": "1.27.2"})
        if path == "/api/v1/user": return self._send(200, {"id": 7, "login": "hermes-bot", "email": "should-not-leak@example.com"})
        if path == "/api/v1/settings/api": return self._send(200, {"max_response_items": 50, "secret_setting": "omit"})
        if path == "/swagger.v1.json": return self._send(200, {"swagger": "2.0", "info": {"title": "Gitea API"}, "paths": {"/repos/{owner}/{repo}": {"get": {"operationId": "repoGet", "summary": "Get repo", "tags": ["repository"]}}}})
        if path == "/api/v1/repos/search": return self._send(200, {"ok": True, "data": [{"id": 1, "name": "r", "private": True}]})
        if path == "/api/v1/repos/o/r/actions/jobs/9/logs": return self._send(200, "Authorization: token secret-token\npassword=hunter2\nok", "text/plain")
        if path in {"/api/v1/repos/o/r/actions/runs", "/api/v1/repos/o/r/actions/workflows/build.yml/runs"}: return self._send(200, {"total_count": 0, "workflow_runs": []})
        if path == "/api/v1/repos/o/r/actions/runs/5/jobs": return self._send(200, {"total_count": 0, "jobs": []})
        if path == "/api/v1/repos/o/r/actions/runs/5/artifacts": return self._send(200, {"total_count": 0, "artifacts": []})
        if path == "/api/v1/repos/o/r/actions/runners": return self._send(200, {"total_count": 0, "runners": []})
        if path == "/api/v1/repos/o/r/branches":
            page = int(query.get("page", ["1"])[0])
            limit = int(query.get("limit", ["2"])[0])
            batches = {1: [{"name": "a"}, {"name": "b"}], 2: [{"name": "c"}]}
            return self._send(200, batches.get(page, [])[:limit])
        return self._send(404, {"message": "not found"})
    def do_POST(self):
        Handler.posts += 1
        return self._send(503, {"message": "temporary"})


class HttpBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.mod = load_plugin()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def setUp(self):
        Handler.posts = 0; Handler.auth_headers = []; Handler.requests = []
        os.environ["GITEA_BASE_URL"] = self.base
        os.environ["GITEA_TOKEN"] = "secret-token"
        os.environ["GITEA_ALLOW_HTTP"] = "1"
        os.environ.pop("GITEA_INSECURE_TLS", None)

    def test_connection_status_is_sanitized_and_authenticated(self):
        data = json.loads(self.mod.HANDLERS["gitea_connection_status"]({}))
        self.assertTrue(data["ok"])
        payload = data["data"]
        self.assertEqual("hermes-bot", payload["account"]["username"])
        self.assertNotIn("email", json.dumps(payload).lower())
        self.assertEqual({"max_response_items": 50}, payload["api_settings"])
        self.assertIn("token secret-token", [x for x in Handler.auth_headers if x])
        self.assertNotIn("secret-token", json.dumps(data))

    def test_get_pagination(self):
        data = json.loads(self.mod.HANDLERS["gitea_repos_list"]({"limit": 30, "max_pages": 2}))
        self.assertTrue(data["ok"])
        self.assertEqual(1, len(data["data"]["items"]))
        self.assertEqual("owned_or_contributed", data["data"]["scope"])
        self.assertEqual(7, data["data"]["authenticated_user_id"])

    def test_job_logs_redact_api_token_and_common_secret_assignments(self):
        data = json.loads(self.mod.HANDLERS["gitea_actions_job_logs"]({"owner": "o", "repo": "r", "job_id": 9}))
        self.assertTrue(data["ok"])
        logs = data["data"]["logs"]
        self.assertNotIn("secret-token", logs)
        self.assertNotIn("hunter2", logs)
        self.assertIn("<redacted>", logs)

    def test_mutating_post_is_not_retried(self):
        data = json.loads(self.mod.HANDLERS["gitea_issue_comment"]({"owner": "o", "repo": "r", "index": 1, "body": "hello"}))
        self.assertFalse(data["ok"])
        self.assertEqual(1, Handler.posts)

    def test_generic_pagination_can_finish_on_exact_max_pages(self):
        data = json.loads(self.mod.HANDLERS["gitea_branches_list"]({"owner": "o", "repo": "r", "limit": 2, "max_pages": 2}))
        self.assertTrue(data["ok"])
        self.assertEqual(3, len(data["data"]["items"]))
        self.assertFalse(data["data"]["truncated"])

    def test_actions_workflow_id_selects_workflow_specific_endpoint(self):
        data = json.loads(self.mod.HANDLERS["gitea_actions_runs"]({"owner": "o", "repo": "r", "workflow_id": "build.yml", "actor": "alice", "exclude_pull_requests": True}))
        self.assertTrue(data["ok"])
        path, query = Handler.requests[-1]
        self.assertEqual("/api/v1/repos/o/r/actions/workflows/build.yml/runs", path)
        self.assertEqual(["alice"], query.get("actor"))
        self.assertEqual(["True"], query.get("exclude_pull_requests"))
        self.assertNotIn("workflow_id", query)

    def test_actions_jobs_uses_documented_filters(self):
        data = json.loads(self.mod.HANDLERS["gitea_actions_jobs"]({"owner": "o", "repo": "r", "run_id": 5, "status": "failure", "limit": 20, "page": 2, "order": "desc"}))
        self.assertTrue(data["ok"])
        path, query = Handler.requests[-1]
        self.assertEqual("/api/v1/repos/o/r/actions/runs/5/jobs", path)
        self.assertEqual(["failure"], query.get("status"))
        self.assertEqual(["20"], query.get("limit"))
        self.assertEqual(["2"], query.get("page"))
        self.assertEqual(["id"], query.get("sort"))
        self.assertEqual(["desc"], query.get("order"))

    def test_actions_artifacts_supports_name_filter(self):
        data = json.loads(self.mod.HANDLERS["gitea_actions_artifacts"]({"owner": "o", "repo": "r", "run_id": 5, "name": "dist"}))
        self.assertTrue(data["ok"])
        path, query = Handler.requests[-1]
        self.assertEqual("/api/v1/repos/o/r/actions/runs/5/artifacts", path)
        self.assertEqual(["dist"], query.get("name"))

    def test_runners_only_uses_documented_disabled_filter(self):
        data = json.loads(self.mod.HANDLERS["gitea_runners_list"]({"owner": "o", "repo": "r", "disabled": False}))
        self.assertTrue(data["ok"])
        path, query = Handler.requests[-1]
        self.assertEqual("/api/v1/repos/o/r/actions/runners", path)
        self.assertEqual(["False"], query.get("disabled"))
        self.assertNotIn("page", query)
        self.assertNotIn("limit", query)


if __name__ == "__main__":
    unittest.main()
