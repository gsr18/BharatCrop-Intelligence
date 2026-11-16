from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from weather_intelligence.archive import audit_archive
from weather_intelligence.dataset import build_canonical_dataset
from weather_intelligence.features import describe_feature_schema
from weather_intelligence.manifest import (
    canonical_json_bytes,
    read_json,
    verify_manifest_digest,
    write_immutable_json,
)
from weather_intelligence.runtime import peak_working_set_bytes, record_benchmark


def _defaults() -> dict[str, Path]:
    workspace_root = Path(__file__).resolve().parents[2]
    repository_root = workspace_root.parent
    return {
        "repository_root": repository_root,
        "workspace_root": workspace_root,
        "config": workspace_root / "config" / "pipeline_v1.json",
        "source_root": repository_root / "data" / "raw" / "weather_regional",
        "manifest": workspace_root / "manifests" / "source_manifest_v1.json",
        "quality_report": workspace_root / "reports" / "source_quality_v1.json",
        "feature_schema": workspace_root / "schemas" / "weather_feature_schema_v1.json",
        "dataset": workspace_root / "data" / "processed" / "weather_daily_v1",
        "benchmark": workspace_root / "reports" / "runtime_benchmark.json",
    }


def _load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot load pipeline config {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"Pipeline config must be a JSON object: {path}")
    return value


def _paths(args: argparse.Namespace) -> dict[str, Path]:
    defaults = _defaults()
    root = Path(args.repository_root).resolve() if args.repository_root else defaults["repository_root"]
    workspace = root / "phase3b_weather_intelligence"
    return {
        "repository_root": root,
        "workspace_root": workspace,
        "config": Path(args.config).resolve() if args.config else workspace / "config" / "pipeline_v1.json",
        "source_root": Path(args.source_root).resolve() if args.source_root else root / "data" / "raw" / "weather_regional",
        "manifest": Path(args.manifest).resolve() if args.manifest else workspace / "manifests" / "source_manifest_v1.json",
        "quality_report": Path(args.quality_report).resolve() if args.quality_report else workspace / "reports" / "source_quality_v1.json",
        "feature_schema": workspace / "schemas" / "weather_feature_schema_v1.json",
        "dataset": Path(args.output).resolve() if args.output else workspace / "data" / "processed" / "weather_daily_v1",
        "benchmark": workspace / "reports" / "runtime_benchmark.json",
    }


def _audit(paths: dict[str, Path], config: dict[str, Any]) -> dict[str, Any]:
    audit = audit_archive(
        paths["source_root"],
        config,
        source_root_label=Path(config["source_root"]).as_posix(),
    )
    write_immutable_json(paths["manifest"], audit.manifest)
    write_immutable_json(paths["quality_report"], audit.quality_report)
    feature_schema = describe_feature_schema(config)
    write_immutable_json(paths["feature_schema"], feature_schema)
    return {
        "manifest_sha256": audit.manifest["manifest_sha256"],
        "manifest_path": str(paths["manifest"]),
        "quality_report_path": str(paths["quality_report"]),
        "feature_schema_path": str(paths["feature_schema"]),
        "source_files": audit.quality_report["source_files"],
        "cells": audit.quality_report["grid_cells"],
        "canonical_rows": audit.quality_report["canonical_rows"],
        "measurements_total": audit.quality_report["measurements_total"],
        "quality_checks": audit.quality_report["checks"],
    }


def _build(paths: dict[str, Path], config: dict[str, Any]) -> dict[str, Any]:
    manifest = read_json(paths["manifest"])
    verify_manifest_digest(manifest)
    return build_canonical_dataset(
        paths["source_root"], manifest, config, paths["dataset"]
    )


def _record_run(
    paths: dict[str, Path],
    *,
    command: str,
    start: datetime,
    monotonic_start: float,
    outputs: dict[str, Any],
) -> dict[str, Any]:
    return record_benchmark(
        paths["benchmark"],
        command=command,
        started_at=start,
        elapsed_seconds=time.perf_counter() - monotonic_start,
        peak_rss_bytes=peak_working_set_bytes(),
        outputs=outputs,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the independent weather-only daily panel from raw POWER/MERRA-2 JSON."
    )
    parser.add_argument("command", choices=("audit", "build", "run"))
    parser.add_argument("--repository-root", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--quality-report", type=Path)
    parser.add_argument("--output", type=Path, help="Canonical dataset output directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = _paths(args)
    config = _load_config(paths["config"])
    started_at = datetime.now(UTC)
    monotonic_start = time.perf_counter()
    try:
        if args.command in {"audit", "run"}:
            audit_summary = _audit(paths, config)
        else:
            audit_summary = None
        if args.command in {"build", "run"}:
            if audit_summary is None:
                feature_schema = describe_feature_schema(config)
                write_immutable_json(paths["feature_schema"], feature_schema)
            dataset = _build(paths, config)
            dataset_summary = {
                "dataset_version": dataset["dataset_version"],
                "dataset_path": str(paths["dataset"]),
                "manifest_sha256": dataset["manifest_sha256"],
                "feature_schema_sha256": dataset["feature_schema_sha256"],
                "canonical_rows": dataset["canonical_rows"],
                "cell_count": dataset["cell_count"],
                "partition_count": len(dataset["partitions"]),
                "parquet_bytes": dataset["storage"]["parquet_bytes"],
                "parquet_mib": dataset["storage"]["parquet_mib"],
                "reused_existing": dataset["reused_existing"],
            }
        else:
            dataset_summary = None
        outputs = {"audit": audit_summary, "dataset": dataset_summary}
        benchmark = _record_run(
            paths,
            command=args.command,
            start=started_at,
            monotonic_start=monotonic_start,
            outputs=outputs,
        )
        print(
            json.dumps(
                {"outputs": outputs, "benchmark": benchmark}, indent=2, sort_keys=True
            )
        )
        return 0
    except Exception as error:
        print(f"Weather-only pipeline stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
