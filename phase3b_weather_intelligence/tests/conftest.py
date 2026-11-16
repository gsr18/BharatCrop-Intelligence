from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WORKSPACE_ROOT.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))


@pytest.fixture
def repository_root() -> Path:
    return REPOSITORY_ROOT


@pytest.fixture
def workspace_root() -> Path:
    return WORKSPACE_ROOT


@pytest.fixture
def config(workspace_root: Path) -> dict[str, object]:
    return json.loads(
        (workspace_root / "config" / "pipeline_v1.json").read_text(encoding="utf-8")
    )
