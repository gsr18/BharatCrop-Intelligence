from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from weather_intelligence.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
