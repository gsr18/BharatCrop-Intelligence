import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bharatcrop_foundation.preservation_check import (
    MANIFEST_SCHEMA,
    compare_manifests,
    inventory,
    load_manifest,
)


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class PreservationCheckTests(unittest.TestCase):
    def test_detects_added_changed_and_deleted_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root / "data" / "changed.csv", b"before")
            _write(root / "docs" / "deleted.md", b"keep")
            baseline = inventory(root)

            _write(root / "data" / "changed.csv", b"after")
            (root / "docs" / "deleted.md").unlink()
            _write(root / "reports" / "new.json", b"new")

            report = compare_manifests(baseline, inventory(root), str(root))

            self.assertEqual(report["status"], "unexpected_changes")
            self.assertEqual(
                report["counts"],
                {
                    "added": 1,
                    "changed": 1,
                    "deleted": 1,
                    "unexpected": 3,
                },
            )
            self.assertEqual(report["changed"][0]["path"], "data/changed.csv")
            self.assertEqual(report["deleted"][0]["path"], "docs/deleted.md")
            self.assertEqual(report["added"][0]["path"], "reports/new.json")

    def test_allows_additions_only_under_application_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root / "data" / "original.csv", b"original")
            baseline = inventory(root)
            _write(root / "application" / "backend" / "new.py", b"new")

            report = compare_manifests(baseline, inventory(root), str(root))

            self.assertEqual(report["status"], "clean")
            self.assertEqual(report["added"][0]["path"], "application/backend/new.py")
            self.assertEqual(report["counts"]["unexpected"], 0)

    def test_flags_additions_outside_application_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            baseline = inventory(root)
            _write(root / "metadata" / "unexpected.json", b"new")

            report = compare_manifests(baseline, inventory(root), str(root))

            self.assertEqual(report["status"], "unexpected_changes")
            self.assertEqual(
                report["unexpected"]["added_paths_outside_approved_workspace"],
                ["metadata/unexpected.json"],
            )

    def test_excludes_only_known_application_build_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root / "application" / "frontend" / "node_modules" / "pkg" / "index.js", b"x")
            _write(root / "application" / "frontend" / "tsconfig.tsbuildinfo", b"x")
            _write(root / "application" / "backend" / ".mypy_cache" / "cache.db", b"x")
            _write(root / "application" / "frontend" / "src" / "page.tsx", b"x")

            paths = inventory(root)

            self.assertEqual(list(paths), ["application/frontend/src/page.tsx"])

    def test_loads_external_manifest_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            content = b"fixture"
            file_hash = hashlib.sha256(content).hexdigest()
            manifest_path = root / "baseline.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema": MANIFEST_SCHEMA,
                        "root": str(root),
                        "file_count": 1,
                        "files": [
                            {
                                "path": "data/sample.csv",
                                "size_bytes": len(content),
                                "sha256": file_hash,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            manifest_root, records = load_manifest(manifest_path)

            self.assertEqual(manifest_root, str(root))
            self.assertEqual(records["data/sample.csv"].sha256, file_hash)


class BackendScaffoldTests(unittest.TestCase):
    def test_app_factory_exposes_openapi_docs_only(self) -> None:
        from bharatcrop_foundation.app import create_app
        from bharatcrop_foundation.config import Settings

        application = create_app(Settings(database_url=None))
        self.assertIsNotNone(application.openapi_url)
        self.assertIsNotNone(application.docs_url)
        self.assertIsNone(application.redoc_url)


if __name__ == "__main__":
    unittest.main()
