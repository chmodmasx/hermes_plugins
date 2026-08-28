from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from gitea_client import GiteaClient, GiteaError, Response  # noqa: E402


class FakeHTTPResponse:
    def __init__(self, status=200, body=b'{}', headers=None, url='https://git.example/api/v1/version'):
        self.status = status
        self._body = body
        self.headers = headers or {"Content-Type": "application/json"}
        self._url = url

    def read(self):
        return self._body

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ClientTests(unittest.TestCase):
    def test_http_rejected_by_default(self):
        with self.assertRaises(GiteaError) as ctx:
            GiteaClient("http://git.local", "x")
        self.assertEqual(ctx.exception.code, "E_INSECURE_TRANSPORT")

    def test_http_explicitly_allowed(self):
        client = GiteaClient("http://git.local", "x", allow_http=True)
        self.assertEqual(client.api_url, "http://git.local/api/v1")

    def test_token_is_sent_in_header_not_url(self):
        client = GiteaClient("https://git.example", "super-secret")
        captured = {}

        def fake_urlopen(req, **kwargs):
            captured["url"] = req.full_url
            captured["auth"] = req.headers.get("Authorization")
            return FakeHTTPResponse(body=b'{"version":"1.27.2"}', url=req.full_url)

        with patch.object(client.opener, "open", side_effect=fake_urlopen):
            data = client.server_version()

        self.assertEqual(data["version"], "1.27.2")
        self.assertEqual(captured["auth"], "token super-secret")
        self.assertNotIn("super-secret", captured["url"])

    def test_swagger_root_request_does_not_send_api_token(self):
        client = GiteaClient("https://git.example", "super-secret")
        captured = {}

        def fake_open(req, **kwargs):
            captured["auth"] = req.headers.get("Authorization")
            return FakeHTTPResponse(
                body=b'{"openapi":"3.0.3","paths":{}}',
                url=req.full_url,
            )

        with patch.object(client.opener, "open", side_effect=fake_open):
            spec = client.swagger()
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertIsNone(captured["auth"])

    def test_redirects_are_refused_before_credentials_can_follow(self):
        client = GiteaClient("https://git.example", "super-secret")
        err = urllib.error.HTTPError(
            "https://git.example/api/v1/version",
            302,
            "Found",
            {"Location": "https://evil.example/steal"},
            None,
        )
        err.fp = __import__("io").BytesIO(b"")
        with patch.object(client.opener, "open", side_effect=err):
            with self.assertRaises(GiteaError) as ctx:
                client.server_version()
        self.assertEqual(ctx.exception.code, "E_REDIRECT")
        self.assertIn("canonical Gitea base URL", ctx.exception.message)

    def test_sensitive_request_values_are_redacted_from_http_errors(self):
        client = GiteaClient("https://git.example", "api-token")
        secret = "do-not-leak-this"
        err = urllib.error.HTTPError(
            "https://git.example/api/v1/repos/o/r/actions/secrets/X",
            422,
            "Unprocessable Entity",
            {"Content-Type": "application/json"},
            __import__("io").BytesIO(
                ("{\"message\":\"bad value do-not-leak-this\",\"echo\":\"do-not-leak-this\"}").encode()
            ),
        )
        with patch.object(client.opener, "open", side_effect=err):
            with self.assertRaises(GiteaError) as ctx:
                client.request(
                    "PUT", "/repos/o/r/actions/secrets/X",
                    body={"data": secret}, sensitive_values=[secret],
                )
        rendered = str(ctx.exception.message) + repr(ctx.exception.details)
        self.assertNotIn(secret, rendered)
        self.assertIn("<redacted>", rendered)

    def test_absolute_api_path_rejected(self):
        client = GiteaClient("https://git.example", "x")
        with self.assertRaises(GiteaError):
            client.request("GET", "https://evil.example/x")

    def test_pagination_collects_all_pages(self):
        client = GiteaClient("https://git.example", "x")
        pages = {
            1: Response(200, {"Link": '<https://git.example/api/v1/x?page=2>; rel="next"'}, [1, 2], ""),
            2: Response(200, {}, [3], ""),
        }

        def fake_request(method, path, query=None, **kwargs):
            return pages[int(query["page"])]

        client.request = fake_request  # type: ignore[method-assign]
        result = client.paginate("/x", limit=2)
        self.assertEqual(result["items"], [1, 2, 3])
        self.assertEqual(result["pages"], 2)

    def test_swagger_search(self):
        client = GiteaClient("https://git.example", "x")
        client.swagger = lambda: {
            "paths": {
                "/repos/{owner}/{repo}/pulls/{index}/merge": {
                    "post": {
                        "operationId": "repoMergePullRequest",
                        "summary": "Merge a pull request",
                        "tags": ["repository"],
                        "parameters": [],
                    }
                },
                "/version": {
                    "get": {
                        "operationId": "getVersion",
                        "summary": "Version",
                        "tags": ["miscellaneous"],
                    }
                },
            }
        }  # type: ignore[method-assign]
        matches = client.search_swagger("merge", method="POST")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["method"], "POST")
        self.assertIn("/merge", matches[0]["path"])


if __name__ == "__main__":
    unittest.main()
