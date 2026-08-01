"""Local read-model sidecar: the first `SecureGuideClient` transport.

A loopback-only HTTP server that exposes the `read-model-v1` surfaces of
:class:`~secureguide.read_models.ReadModel` as JSON. The Flutter app talks to
this over `127.0.0.1`, so the mature Python core stays the single source of
business logic — nothing is reimplemented in Dart. Governed writes are exposed
through the symmetric write contract (`POST /write/...`).

Routing is a pure function, :func:`resolve`, so it is unit-tested against the
golden fixtures without opening a socket. Domain errors map to HTTP status
codes; the body is always JSON.

Run::

    python -m secureguide.sidecar --db dist/secureguide-demo.db
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .database import Database
from .errors import AuthorizationError, NotFoundError, ValidationError
from .read_models import CONTRACT_VERSION, ReadModel
from .services import SecureGuideService
from .write_models import WriteModel

__all__ = ["resolve", "resolve_write", "build_server", "SidecarServer", "main"]


def _first(query: dict[str, list[str]], name: str, default: str | None = None) -> str | None:
    values = query.get(name)
    return values[0] if values else default


def _as_int(query: dict[str, list[str]], name: str, default: int) -> int:
    raw = _first(query, name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError(f"query param {name} must be an integer") from exc


def _as_bool(query: dict[str, list[str]], name: str, default: bool = False) -> bool:
    raw = _first(query, name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _error_response(exc: Exception) -> tuple[int, dict[str, Any]]:
    """Map a domain error to an HTTP status + JSON body (never leaks a trace)."""
    if isinstance(exc, NotFoundError):
        return 404, {"error": "NotFoundError", "message": str(exc)}
    if isinstance(exc, ValidationError):  # includes ActiveProfileRequiredError
        return 400, {"error": type(exc).__name__, "message": str(exc)}
    if isinstance(exc, AuthorizationError):
        return 403, {"error": "AuthorizationError", "message": str(exc)}
    return 500, {"error": "InternalError", "message": str(exc)}


def resolve(
    read_model: ReadModel, path: str, query: dict[str, list[str]]
) -> tuple[int, dict[str, Any]]:
    """Map a GET path + query to an HTTP status and a wire payload (pure)."""
    parts = [segment for segment in path.split("/") if segment]
    try:
        if parts == ["health"]:
            return 200, {"status": "ok", "contractVersion": CONTRACT_VERSION}
        if parts == ["read", "profiles"]:
            return 200, read_model.profiles()
        if parts == ["read", "active-profile"]:
            return 200, read_model.active_profile()
        if parts == ["read", "dashboard"]:
            return 200, read_model.dashboard(
                profile_id=_first(query, "profileId"),
                gap_limit=_as_int(query, "gapLimit", 20),
            )
        if parts == ["read", "catalog"]:
            return 200, read_model.catalog(
                profile_id=_first(query, "profileId"),
                locale=_first(query, "locale", "en") or "en",
                query=_first(query, "query"),
                selected_only=_as_bool(query, "selectedOnly"),
                limit=_as_int(query, "limit", 100),
                offset=_as_int(query, "offset", 0),
            )
        if len(parts) == 3 and parts[:2] == ["read", "profile-artifacts"]:
            return 200, read_model.profile_artifact(
                parts[2], profile_id=_first(query, "profileId")
            )
        if parts == ["read", "blueprints"]:
            return 200, read_model.blueprints(
                profile_id=_first(query, "profileId"),
                artifact_id=_first(query, "artifactId"),
                workflow_status=_first(query, "workflowStatus"),
            )
        if len(parts) == 3 and parts[0] == "read" and parts[1] == "blueprints":
            return 200, read_model.blueprint(parts[2], profile_id=_first(query, "profileId"))
        if parts == ["read", "tasks"]:
            return 200, read_model.tasks(
                profile_id=_first(query, "profileId"), status=_first(query, "status")
            )
        if parts == ["read", "report"]:
            return 200, read_model.report(profile_id=_first(query, "profileId"))
        return 404, {"error": "NotFound", "message": f"unknown route: /{'/'.join(parts)}"}
    except Exception as exc:  # noqa: BLE001 (mapped to a JSON error body)
        return _error_response(exc)


def resolve_write(
    write_model: WriteModel, path: str, body: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    """Map a POST path + JSON body to an HTTP status and a wire payload (pure)."""
    parts = [segment for segment in path.split("/") if segment]
    try:
        if parts == ["write", "profiles"]:
            return 200, write_model.create_profile(body)
        if parts == ["write", "active-profile"]:
            return 200, write_model.activate_profile(body)
        if parts == ["write", "select-artifacts"]:
            return 200, write_model.select_artifacts(body)
        if parts == ["write", "assessments"]:
            return 200, write_model.assess_artifact(body)
        if parts == ["write", "templates", "apply"]:
            return 200, write_model.apply_template(body)
        if parts == ["write", "evidence"]:
            return 200, write_model.add_evidence(body)
        if parts == ["write", "exceptions"]:
            return 200, write_model.create_exception(body)
        return 404, {"error": "NotFound", "message": f"unknown route: /{'/'.join(parts)}"}
    except Exception as exc:  # noqa: BLE001 (mapped to a JSON error body)
        return _error_response(exc)


class _Handler(BaseHTTPRequestHandler):
    server_version = "SecureGuideSidecar/1.0"

    def _send(self, status: int, payload: dict[str, Any], *, allow_cors: bool = False) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if allow_cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        parsed = urlparse(self.path)
        status, payload = resolve(self.server.read_model, parsed.path, parse_qs(parsed.query))
        self._send(status, payload, allow_cors=True)

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(body, dict):
                raise ValueError("body must be a JSON object")
        except (ValueError, UnicodeDecodeError) as exc:
            self._send(400, {"error": "BadRequest", "message": f"invalid JSON body: {exc}"})
            return
        parsed = urlparse(self.path)
        status, payload = resolve_write(self.server.write_model, parsed.path, body)
        self._send(status, payload)

    def do_OPTIONS(self) -> None:  # noqa: N802 (CORS preflight for browser clients)
        self.send_response(204)
        req_method = self.headers.get("Access-Control-Request-Method", "")
        if req_method.upper() == "GET":
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, *args: Any) -> None:  # keep the console quiet
        return


class SidecarServer(HTTPServer):
    """Single-threaded HTTP server holding a ready read + write model pair."""

    def __init__(
        self, address: tuple[str, int], read_model: ReadModel, write_model: WriteModel
    ):
        super().__init__(address, _Handler)
        self.read_model = read_model
        self.write_model = write_model


def build_server(
    db_path: str | Path, *, host: str = "127.0.0.1", port: int = 8765
) -> SidecarServer:
    service = SecureGuideService(Database(str(db_path)))
    return SidecarServer((host, port), ReadModel(service), WriteModel(service))


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Run the local read-model sidecar.")
    parser.add_argument("--db", type=Path, default=root / "dist" / "secureguide-demo.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if not Path(args.db).exists():
        raise SystemExit(
            f"database not found: {args.db}\n"
            "build one first: python -m scripts.build_release_db"
        )
    server = build_server(args.db, host=args.host, port=args.port)
    host, port = server.server_address
    print(f"SecureGuide sidecar on http://{host}:{port}  (db={args.db})")
    print("  GET  /health · /read/profiles · /read/dashboard?profileId=…")
    print("  GET  /read/profile-artifacts/{artifactId}?profileId=…")
    print("  POST /write/profiles · /write/select-artifacts · /write/assessments")
    print("  Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
