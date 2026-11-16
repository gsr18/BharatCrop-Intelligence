from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_SCHEMA = "bharatcrop-preservation-manifest-v1"
APPROVED_ADDITION_PREFIXES = ("application/",)
GENERATED_APPLICATION_DIRECTORIES = {
    ".next",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "coverage",
    "node_modules",
}
GENERATED_APPLICATION_FILES = {"application/frontend/tsconfig.tsbuildinfo"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class FileRecord:
    size_bytes: int
    sha256: str


def _safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Manifest path must be a non-empty string")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Unsafe manifest path: {value!r}")
    return path.as_posix()


def _record_from_value(value: Any, relative_path: str) -> FileRecord:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid record for {relative_path!r}")
    size_bytes = value.get("size_bytes")
    sha256 = value.get("sha256")
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
        raise ValueError(f"Invalid file size for {relative_path!r}")
    if not isinstance(sha256, str) or not SHA256_PATTERN.fullmatch(sha256):
        raise ValueError(f"Invalid SHA-256 for {relative_path!r}")
    return FileRecord(size_bytes=size_bytes, sha256=sha256)


def load_manifest(path: Path) -> tuple[str, dict[str, FileRecord]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("Unsupported or malformed preservation manifest")
    root = data.get("root")
    entries = data.get("files")
    if not isinstance(root, str) or not isinstance(entries, list):
        raise ValueError("Manifest must contain a root and file list")

    records: dict[str, FileRecord] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Manifest file entry must be an object")
        relative_path = _safe_relative_path(entry.get("path"))
        if relative_path in records:
            raise ValueError(f"Duplicate manifest path: {relative_path}")
        records[relative_path] = _record_from_value(entry, relative_path)
    if data.get("file_count") != len(records):
        raise ValueError("Manifest file_count does not match its entries")
    return root, records


def _is_generated_application_path(relative_path: str) -> bool:
    parts = PurePosixPath(relative_path).parts
    return (
        len(parts) > 1
        and parts[0] == "application"
        and any(part in GENERATED_APPLICATION_DIRECTORIES for part in parts[1:])
    )


def inventory(root: Path) -> dict[str, FileRecord]:
    root = root.resolve(strict=True)
    records: dict[str, FileRecord] = {}
    for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        relative_directory = directory_path.relative_to(root).as_posix()
        if relative_directory == ".":
            relative_directory = ""
        if relative_directory == "application":
            dirnames[:] = [
                name for name in dirnames if name not in GENERATED_APPLICATION_DIRECTORIES
            ]
        elif relative_directory.startswith("application/"):
            dirnames[:] = [
                name for name in dirnames if name not in GENERATED_APPLICATION_DIRECTORIES
            ]

        for filename in filenames:
            file_path = directory_path / filename
            relative_path = file_path.relative_to(root).as_posix()
            if (
                _is_generated_application_path(relative_path)
                or relative_path in GENERATED_APPLICATION_FILES
            ):
                continue
            digest = hashlib.sha256()
            size_bytes = 0
            with file_path.open("rb") as file_stream:
                for block in iter(lambda: file_stream.read(1024 * 1024), b""):
                    digest.update(block)
                    size_bytes += len(block)
            records[relative_path] = FileRecord(
                size_bytes=size_bytes,
                sha256=digest.hexdigest(),
            )
    return records


def compare_manifests(
    baseline: dict[str, FileRecord],
    current: dict[str, FileRecord],
    root: str,
) -> dict[str, Any]:
    baseline_paths = set(baseline)
    current_paths = set(current)
    added_paths = sorted(current_paths - baseline_paths)
    deleted_paths = sorted(baseline_paths - current_paths)
    changed_paths = sorted(
        path for path in baseline_paths & current_paths if baseline[path] != current[path]
    )
    unexpected_additions = [
        path
        for path in added_paths
        if not any(path.startswith(prefix) for prefix in APPROVED_ADDITION_PREFIXES)
    ]

    added = [{"path": path, **asdict(current[path])} for path in added_paths]
    changed = [
        {
            "path": path,
            "before": asdict(baseline[path]),
            "after": asdict(current[path]),
        }
        for path in changed_paths
    ]
    deleted = [{"path": path, **asdict(baseline[path])} for path in deleted_paths]
    unexpected = {
        "added_paths_outside_approved_workspace": unexpected_additions,
        "changed_preexisting_paths": changed,
        "deleted_preexisting_paths": deleted,
    }
    has_unexpected_changes = any(unexpected.values())

    return {
        "schema": "bharatcrop-preservation-comparison-v1",
        "root": root,
        "status": "unexpected_changes" if has_unexpected_changes else "clean",
        "counts": {
            "added": len(added),
            "changed": len(changed),
            "deleted": len(deleted),
            "unexpected": len(unexpected_additions) + len(changed) + len(deleted),
        },
        "added": added,
        "changed": changed,
        "deleted": deleted,
        "unexpected": unexpected,
        "generated_application_directories_excluded": sorted(GENERATED_APPLICATION_DIRECTORIES),
        "generated_application_files_excluded": sorted(GENERATED_APPLICATION_FILES),
        "approved_addition_prefixes": list(APPROVED_ADDITION_PREFIXES),
    }


def _same_root(manifest_root: str, current_root: Path) -> bool:
    return os.path.normcase(os.path.abspath(manifest_root)) == os.path.normcase(
        str(current_root.resolve(strict=True))
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare workspace paths and SHA-256 hashes against an approved baseline."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        root = args.root.resolve(strict=True)
        manifest_root, baseline = load_manifest(args.baseline)
        if not _same_root(manifest_root, root):
            raise ValueError("Baseline root does not match the requested workspace root")
        current = inventory(root)
        report = compare_manifests(baseline, current, str(root))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"preservation check failed: {error}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["status"] != "clean" else 0


if __name__ == "__main__":
    raise SystemExit(main())
