from __future__ import annotations

import ctypes
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from ctypes import wintypes


def peak_working_set_bytes() -> int | None:
    """Return process peak RSS/working set using OS APIs, without an extra package."""
    if os.name == "nt":
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            return None
        return int(counters.PeakWorkingSetSize)

    try:
        import resource

        peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return peak if sys.platform == "darwin" else peak * 1024
    except (ImportError, AttributeError, OSError):
        return None


def software_versions() -> dict[str, str]:
    import numpy
    import pandas
    import pyarrow

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": numpy.__version__,
        "pandas": pandas.__version__,
        "pyarrow": pyarrow.__version__,
    }


def record_benchmark(
    report_path: Path,
    *,
    command: str,
    started_at: datetime,
    elapsed_seconds: float,
    peak_rss_bytes: int | None,
    outputs: dict[str, Any],
) -> dict[str, Any]:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {"schema_version": "1.0.0", "runs": []}
    else:
        report = {"schema_version": "1.0.0", "runs": []}
    run = {
        "command": command,
        "started_at_utc": started_at.astimezone(UTC).isoformat(),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "peak_working_set_bytes": peak_rss_bytes,
        "peak_working_set_mib": (
            round(peak_rss_bytes / (1024 * 1024), 2) if peak_rss_bytes is not None else None
        ),
        "software_versions": software_versions(),
        "outputs": outputs,
    }
    report.setdefault("runs", []).append(run)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run
