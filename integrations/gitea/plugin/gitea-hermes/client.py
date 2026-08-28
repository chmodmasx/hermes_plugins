from __future__ import annotations

import json
import os
import random
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Iterable, Mapping


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
TRANSIENT_STATUSES = {408, 425, 429, 500, 502, 503, 504}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Block redirects so Authorization can never be forwarded to another origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


@dataclass
class GiteaError(Exception):
    code: str
    message: str
    status: int | None = None
    retryable: bool = False
    details: Any = None

    def __str__(self) -> str:
        suffix = f" (HTTP {self.status})" if self.status is not None else ""
        return f"{self.code}{suffix}: {self.message}"


@dataclass
class Response:
    status: int
    headers: Mapping[str, str]
    data: Any
    url: str


class GiteaClient:
    """Small stdlib-only Gitea REST client designed for Hermes skills."""

    def __init__(
        self,
        base_url: str,
        token: str | None,
        *,
        timeout: float = 30.0,
        ca_bundle: str | None = None,
        insecure: bool = False,
        allow_http: bool = False,
        user_agent: str = "hermes-gitea-plugin/1.0.0",
        max_attempts: int = 4,
    ) -> None:
        if not base_url:
            raise GiteaError("E_CONFIG", "Gitea base URL is required")
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise GiteaError("E_CONFIG", "Gitea base URL must be an absolute http(s) URL")
        if parsed.query or parsed.fragment:
            raise GiteaError("E_CONFIG", "Gitea base URL must not contain a query string or fragment")
        if parsed.scheme == "http" and not allow_http:
            raise GiteaError(
                "E_INSECURE_TRANSPORT",
                "HTTP is disabled by default; use --allow-http only for a trusted network",
            )
        if parsed.username or parsed.password:
            raise GiteaError("E_CONFIG", "Credentials in the Gitea URL are forbidden")

        self.base_url = base_url.rstrip("/")
        self.api_url = self.base_url + "/api/v1"
        self.token = token
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_attempts = max(1, int(max_attempts))

        if insecure:
            self.ssl_context = ssl._create_unverified_context()  # noqa: SLF001 - deliberate opt-in
        else:
            self.ssl_context = ssl.create_default_context(cafile=ca_bundle)

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(context=self.ssl_context),
            _NoRedirect(),
        )

    @classmethod
    def from_environment(
        cls,
        *,
        base_url: str | None = None,
        token_env: str = "GITEA_TOKEN",
        **kwargs: Any,
    ) -> "GiteaClient":
        resolved_url = base_url or os.environ.get("GITEA_BASE_URL")
        token = os.environ.get(token_env)
        if not resolved_url:
            raise GiteaError(
                "E_CONFIG",
                "No Gitea base URL. Pass --base-url or set GITEA_BASE_URL.",
            )
        return cls(resolved_url, token, **kwargs)

    @staticmethod
    def _decode_body(raw: bytes, content_type: str | None) -> Any:
        if not raw:
            return None
        text = raw.decode("utf-8", errors="replace")
        if content_type and "json" in content_type.lower():
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"_invalid_json": True, "text": text}
        stripped = text.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return text

    @staticmethod
    def _error_code(status: int) -> str:
        return {
            400: "E_BAD_REQUEST",
            401: "E_AUTH_INVALID",
            403: "E_FORBIDDEN",
            404: "E_NOT_FOUND",
            405: "E_METHOD_NOT_ALLOWED",
            409: "E_CONFLICT",
            410: "E_GONE",
            412: "E_PRECONDITION",
            422: "E_VALIDATION",
            423: "E_LOCKED",
            429: "E_RATE_LIMITED",
        }.get(status, "E_REDIRECT" if 300 <= status < 400 else ("E_TRANSIENT" if status >= 500 else "E_HTTP"))

    @staticmethod
    def _redact(value: Any, token: str | None) -> Any:
        if token is None:
            return value
        if isinstance(value, str):
            return value.replace(token, "<redacted>")
        if isinstance(value, list):
            return [GiteaClient._redact(v, token) for v in value]
        if isinstance(value, dict):
            return {k: GiteaClient._redact(v, token) for k, v in value.items()}
        return value

    @staticmethod
    def _redact_many(value: Any, values: Iterable[str | None]) -> Any:
        redacted = value
        for secret in values:
            if secret:
                redacted = GiteaClient._redact(redacted, secret)
        return redacted

    @staticmethod
    def _backoff(attempt: int) -> float:
        return random.uniform(0.25, min(2 ** attempt, 12.0))

    @staticmethod
    def _retry_after(headers: Mapping[str, str], attempt: int) -> float:
        raw = headers.get("Retry-After") or headers.get("retry-after")
        if raw:
            raw = raw.strip()
            if raw.isdigit():
                return min(float(raw), 120.0)
            try:
                dt = parsedate_to_datetime(raw)
                delay = dt.timestamp() - time.time()
                return max(0.0, min(delay, 120.0))
            except Exception:
                pass
        return GiteaClient._backoff(attempt)

    def _headers(self, extra: Mapping[str, str] | None = None, *, send_auth: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if send_auth and self.token:
            headers["Authorization"] = f"token {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def _absolute_api_url(self, path: str, query: Mapping[str, Any] | None = None) -> str:
        if not path.startswith("/"):
            raise GiteaError("E_VALIDATION", "API path must start with '/'")
        parsed = urllib.parse.urlsplit(path)
        if parsed.scheme or parsed.netloc:
            raise GiteaError("E_VALIDATION", "Absolute URLs are forbidden in API paths")
        url = self.api_url + path
        if query:
            encoded = urllib.parse.urlencode(
                [(k, item) for k, value in query.items() for item in (value if isinstance(value, list) else [value]) if item is not None],
                doseq=True,
            )
            if encoded:
                url += ("&" if "?" in url else "?") + encoded
        return url

    def _absolute_root_url(self, path: str) -> str:
        if not path.startswith("/"):
            raise GiteaError("E_VALIDATION", "Root path must start with '/'")
        parsed = urllib.parse.urlsplit(path)
        if parsed.scheme or parsed.netloc:
            raise GiteaError("E_VALIDATION", "Absolute URLs are forbidden")
        return self.base_url + path

    def _perform(
        self,
        method: str,
        url: str,
        *,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        retry_mutation: bool = False,
        sensitive_values: Iterable[str] | None = None,
        send_auth: bool = True,
    ) -> Response:
        method = method.upper()
        payload: bytes | None = None
        req_headers = self._headers(headers, send_auth=send_auth)
        if body is not None:
            payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")

        safe_retry = method in SAFE_METHODS or retry_mutation
        attempts = self.max_attempts if safe_retry else 1

        for attempt in range(1, attempts + 1):
            req = urllib.request.Request(url, data=payload, method=method, headers=req_headers)
            try:
                with self.opener.open(req, timeout=self.timeout) as response:
                    raw = response.read()
                    content_type = response.headers.get("Content-Type")
                    return Response(
                        status=response.status,
                        headers=dict(response.headers.items()),
                        data=self._decode_body(raw, content_type),
                        url=response.geturl(),
                    )
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                response_headers = dict(exc.headers.items()) if exc.headers else {}
                content_type = exc.headers.get("Content-Type") if exc.headers else None
                details = self._decode_body(raw, content_type)
                details = self._redact_many(details, [self.token, *(sensitive_values or [])])
                retryable = exc.code in TRANSIENT_STATUSES
                if retryable and safe_retry and attempt < attempts:
                    time.sleep(self._retry_after(response_headers, attempt))
                    continue
                message = details.get("message") if isinstance(details, dict) else str(details or exc.reason)
                if 300 <= exc.code < 400:
                    location = response_headers.get("Location") or response_headers.get("location")
                    message = f"Redirect refused{': ' + location if location else ''}. Configure the canonical Gitea base URL."
                    details = {"location": location} if location else details
                message = self._redact_many(message, [self.token, *(sensitive_values or [])])
                details = self._redact_many(details, [self.token, *(sensitive_values or [])])
                raise GiteaError(
                    self._error_code(exc.code),
                    message or exc.reason or "HTTP request failed",
                    status=exc.code,
                    retryable=retryable,
                    details=details,
                ) from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if safe_retry and attempt < attempts:
                    time.sleep(self._backoff(attempt))
                    continue
                reason = getattr(exc, "reason", exc)
                raise GiteaError(
                    "E_TRANSIENT",
                    str(reason),
                    retryable=True,
                ) from None

        raise GiteaError("E_TRANSIENT", "Maximum retry attempts exceeded", retryable=True)

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        retry_mutation: bool = False,
        sensitive_values: Iterable[str] | None = None,
    ) -> Response:
        return self._perform(
            method,
            self._absolute_api_url(path, query),
            body=body,
            headers=headers,
            retry_mutation=retry_mutation,
            sensitive_values=sensitive_values,
        )

    def root_request(self, method: str, path: str, *, authenticated: bool = False) -> Response:
        return self._perform(method, self._absolute_root_url(path), send_auth=authenticated)

    def get(self, path: str, *, query: Mapping[str, Any] | None = None) -> Any:
        return self.request("GET", path, query=query).data

    def try_get(self, path: str, *, query: Mapping[str, Any] | None = None) -> Any | None:
        try:
            return self.get(path, query=query)
        except GiteaError as exc:
            if exc.code == "E_NOT_FOUND":
                return None
            raise

    @staticmethod
    def _link_next(headers: Mapping[str, str]) -> str | None:
        raw = headers.get("Link") or headers.get("link")
        if not raw:
            return None
        for part in raw.split(","):
            section = part.strip()
            if 'rel="next"' in section or "rel=next" in section:
                if section.startswith("<") and ">" in section:
                    return section[1:section.index(">")]
        return None

    def paginate(
        self,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        limit: int = 50,
        max_pages: int = 1000,
    ) -> dict[str, Any]:
        base_query = dict(query or {})
        base_query.setdefault("limit", limit)
        page = int(base_query.pop("page", 1))
        items: list[Any] = []
        pages = 0
        total_count: int | None = None

        exhausted = False
        while pages < max_pages:
            q = dict(base_query)
            q["page"] = page
            response = self.request("GET", path, query=q)
            pages += 1
            data = response.data
            if not isinstance(data, list):
                raise GiteaError(
                    "E_SHAPE",
                    "Expected a list response for pagination",
                    status=response.status,
                    details={"received_type": type(data).__name__},
                )
            items.extend(data)
            raw_total = response.headers.get("X-Total-Count") or response.headers.get("x-total-count")
            if raw_total and str(raw_total).isdigit():
                total_count = int(raw_total)

            next_link = self._link_next(response.headers)
            if next_link:
                parsed = urllib.parse.urlsplit(next_link)
                params = urllib.parse.parse_qs(parsed.query)
                next_page = params.get("page", [None])[0]
                if next_page and str(next_page).isdigit():
                    page = int(next_page)
                    continue

            if len(data) < int(base_query.get("limit", limit)):
                exhausted = True
                break
            page += 1

        return {
            "items": items,
            "pages": pages,
            "total_count": total_count,
            "truncated": not exhausted and pages >= max_pages,
        }

    def server_version(self) -> Any:
        return self.get("/version")

    def whoami(self) -> Any:
        if not self.token:
            raise GiteaError("E_AUTH_REQUIRED", "GITEA_TOKEN is required for /user")
        return self.get("/user")

    def swagger(self) -> Any:
        response = self.root_request("GET", "/swagger.v1.json")
        if not isinstance(response.data, dict):
            raise GiteaError("E_SHAPE", "swagger.v1.json did not return a JSON object")
        return response.data

    def search_swagger(
        self,
        term: str,
        *,
        method: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        spec = self.swagger()
        needle = term.lower().strip()
        method_filter = method.upper() if method else None
        tag_filter = tag.lower() if tag else None
        matches: list[dict[str, Any]] = []
        paths = spec.get("paths", {})
        for path, operations in paths.items():
            if not isinstance(operations, dict):
                continue
            for verb, op in operations.items():
                verb_upper = verb.upper()
                if verb_upper not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                    continue
                if method_filter and verb_upper != method_filter:
                    continue
                if not isinstance(op, dict):
                    continue
                tags = [str(x) for x in op.get("tags", [])]
                if tag_filter and not any(tag_filter == t.lower() for t in tags):
                    continue
                haystack = " ".join(
                    [
                        path,
                        verb_upper,
                        str(op.get("operationId", "")),
                        str(op.get("summary", "")),
                        str(op.get("description", "")),
                        " ".join(tags),
                    ]
                ).lower()
                if needle and needle not in haystack:
                    continue
                matches.append(
                    {
                        "method": verb_upper,
                        "path": path,
                        "operation_id": op.get("operationId"),
                        "summary": op.get("summary"),
                        "tags": tags,
                        "parameters": op.get("parameters", []),
                        "request_body": op.get("requestBody"),
                    }
                )
        return matches

    def capability_summary(self) -> dict[str, Any]:
        version = self.server_version()
        try:
            spec = self.swagger()
        except GiteaError as exc:
            return {
                "version": version,
                "swagger_available": False,
                "swagger_error": {"code": exc.code, "message": exc.message},
            }

        tags: dict[str, int] = {}
        total = 0
        for operations in spec.get("paths", {}).values():
            if not isinstance(operations, dict):
                continue
            for verb, op in operations.items():
                if verb.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                    continue
                if not isinstance(op, dict):
                    continue
                total += 1
                for tag in op.get("tags", []) or ["untagged"]:
                    tags[str(tag)] = tags.get(str(tag), 0) + 1
        return {
            "version": version,
            "swagger_available": True,
            "openapi": spec.get("openapi") or spec.get("swagger"),
            "title": (spec.get("info") or {}).get("title"),
            "operation_count": total,
            "operations_by_tag": dict(sorted(tags.items())),
        }


def parse_key_values(values: Iterable[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for raw in values:
        if "=" not in raw:
            raise GiteaError("E_VALIDATION", f"Expected KEY=VALUE, got {raw!r}")
        key, value = raw.split("=", 1)
        if not key:
            raise GiteaError("E_VALIDATION", f"Empty key in {raw!r}")
        if key in result:
            current = result[key]
            if isinstance(current, list):
                current.append(value)
            else:
                result[key] = [current, value]
        else:
            result[key] = value
    return result
