import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import verify_mobile_runtime_boundary


class MobileRuntimeBoundaryTests(unittest.TestCase):
    def _mobile_tree(self, root: Path) -> Path:
        mobile = root / "mobile"
        (mobile / "lib").mkdir(parents=True)
        (mobile / "assets").mkdir()
        (mobile / "android" / "app" / "src" / "main").mkdir(parents=True)
        (mobile / "ios" / "Runner").mkdir(parents=True)
        (mobile / "pubspec.yaml").write_text(
            "name: boundary_fixture\ndependencies:\n  flutter:\n    sdk: flutter\n",
            encoding="utf-8",
        )
        (mobile / "android" / "app" / "src" / "main" / "AndroidManifest.xml").write_text(
            "<manifest />",
            encoding="utf-8",
        )
        return mobile

    def test_local_only_mobile_tree_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mobile = self._mobile_tree(root)
            (mobile / "lib" / "storage.dart").write_text(
                "import 'dart:io';\nFuture<void> save(File file) async {}\n",
                encoding="utf-8",
            )

            with (
                patch.object(verify_mobile_runtime_boundary, "ROOT", root),
                patch.object(verify_mobile_runtime_boundary, "MOBILE", mobile),
            ):
                self.assertEqual([], verify_mobile_runtime_boundary.violations())

    def test_socket_dependency_permission_and_packaged_python_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mobile = self._mobile_tree(root)
            (mobile / "pubspec.yaml").write_text(
                "name: boundary_fixture\ndependencies:\n  grpc: ^4.0.0\n",
                encoding="utf-8",
            )
            (mobile / "lib" / "client.dart").write_text(
                "Future<void> connect() => Socket.connect('host', 443);\n",
                encoding="utf-8",
            )
            (mobile / "assets" / "sidecar.py").write_text(
                "print('sidecar')\n",
                encoding="utf-8",
            )
            manifest = mobile / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
            manifest.write_text(
                '<manifest><uses-permission android:name="android.permission.INTERNET" /></manifest>',
                encoding="utf-8",
            )

            with (
                patch.object(verify_mobile_runtime_boundary, "ROOT", root),
                patch.object(verify_mobile_runtime_boundary, "MOBILE", mobile),
            ):
                findings = verify_mobile_runtime_boundary.violations()

            self.assertTrue(any("grpc" in finding for finding in findings))
            self.assertTrue(any("socket or WebSocket" in finding for finding in findings))
            self.assertTrue(any("INTERNET permission" in finding for finding in findings))
            self.assertTrue(any("Python file packaged" in finding for finding in findings))


if __name__ == "__main__":
    unittest.main()
