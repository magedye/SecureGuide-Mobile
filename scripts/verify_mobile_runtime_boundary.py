"""Fail closed when the released mobile tree acquires a network/sidecar runtime."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MOBILE = ROOT / "mobile"

FORBIDDEN_SOURCE_PATTERNS = {
    "Python sidecar loopback endpoint": re.compile(r"(?:127\.0\.0\.1|localhost)", re.I),
    "Dart HTTP client": re.compile(r"\bHttpClient\s*\("),
    "Dart socket or WebSocket client": re.compile(
        r"\b(?:Socket|RawSocket|SecureSocket|WebSocket)\s*\.\s*connect\s*\("
    ),
    "package:http runtime": re.compile(r"package:http/"),
    "Dio runtime": re.compile(r"package:dio/|\bDio\s*\("),
    "WebSocket runtime": re.compile(r"package:web_socket_channel/"),
    "gRPC runtime": re.compile(r"package:grpc/"),
    "socket.io runtime": re.compile(r"package:socket_io_client/"),
    "MQTT runtime": re.compile(r"package:mqtt_client/"),
    "GraphQL runtime": re.compile(r"package:(?:graphql|graphql_flutter|ferry)/"),
}


def violations() -> list[str]:
    findings: list[str] = []
    pubspec = (MOBILE / "pubspec.yaml").read_text(encoding="utf-8")
    for dependency in (
        "http",
        "dio",
        "chopper",
        "retrofit",
        "web_socket_channel",
        "grpc",
        "socket_io_client",
        "mqtt_client",
        "graphql",
        "graphql_flutter",
        "ferry",
    ):
        if re.search(rf"^\s{{2}}{re.escape(dependency)}\s*:", pubspec, re.M):
            findings.append(f"pubspec runtime dependency: {dependency}")

    for path in sorted((MOBILE / "lib").rglob("*.dart")):
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN_SOURCE_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}")

    manifests = [MOBILE / "android" / "app" / "src" / "main" / "AndroidManifest.xml"]
    for manifest in manifests:
        text = manifest.read_text(encoding="utf-8")
        if "android.permission.INTERNET" in text:
            findings.append(
                f"{manifest.relative_to(ROOT)}: INTERNET permission declared"
            )

    release_roots = [
        MOBILE / "lib",
        MOBILE / "assets",
        MOBILE / "android" / "app" / "src" / "main",
        MOBILE / "ios" / "Runner",
    ]
    packaged_python = sorted(
        path for release_root in release_roots for path in release_root.rglob("*.py")
    )
    findings.extend(
        f"{path.relative_to(ROOT)}: Python file packaged in mobile tree"
        for path in packaged_python
    )
    return findings


def main() -> None:
    findings = violations()
    if findings:
        raise SystemExit(
            "Standalone mobile runtime boundary failed:\n- " + "\n- ".join(findings)
        )
    print(
        "PASS: mobile runtime has no Python, network client, loopback, "
        "or INTERNET permission"
    )


if __name__ == "__main__":
    main()
