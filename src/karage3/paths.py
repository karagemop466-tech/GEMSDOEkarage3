"""Filesystem roots for karage3 (vendored interface: restore_data.py expects data_dir())."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return ROOT / ".cache" / "gems_data"


def work_dir() -> Path:
    p = ROOT / ".cache" / "gems_work"
    p.mkdir(parents=True, exist_ok=True)
    return p


def docs_dir() -> Path:
    return ROOT / "docs"


def evidence_dir() -> Path:
    p = ROOT / "evidence"
    p.mkdir(parents=True, exist_ok=True)
    return p


def registry_dir() -> Path:
    return ROOT / "registry"
