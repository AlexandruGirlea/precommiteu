from __future__ import annotations

from precommiteu.scan import GitDiffError, scan_diff, scan_paths
from precommiteu.src.schemas import Advisory, Finding, ScanResult, ScanStatus

__version__ = "0.2.0"

__all__ = [
    "Advisory",
    "Finding",
    "GitDiffError",
    "ScanResult",
    "ScanStatus",
    "__version__",
    "scan_diff",
    "scan_paths",
]
