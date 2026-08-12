"""Fail-closed verification of public release contents."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "rescue79-hard4-portable-v1.pt"
MODEL_SHA256 = "603cf711a4ccd59119c63a207bb78f3399ce8860c6eed5d6692481f13ff2db0a"
REQUIRED_DOCS = (
    "README.md",
    "QUICK_START_KO.md",
    "INSTALL_WINDOWS_KO.md",
    "RESULT_GUIDE_KO.md",
    "SAFETY_AND_PRIVACY_KO.md",
    "TROUBLESHOOTING_KO.md",
    "MODEL_CARD.md",
    "MODEL_LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
    "ASSET_LICENSE.md",
)
SECRET_PATTERNS = (
    re.compile(r"glpat-[A-Za-z0-9_-]{10,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"PRIVATE-TOKEN\s*[:=]\s*\S+", re.IGNORECASE),
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    for name in REQUIRED_DOCS:
        path = ROOT / name
        if not path.is_file() or path.stat().st_size < 100:
            raise SystemExit(f"Missing or incomplete document: {name}")

    checkpoint = torch.load(MODEL, map_location="cpu", weights_only=True)
    if digest(MODEL) != MODEL_SHA256:
        raise SystemExit("Portable model SHA-256 changed")
    if checkpoint.get("schema_version") != "rescue79-portable-static-model-v1":
        raise SystemExit("Portable model schema mismatch")
    if "E:\\" in repr(checkpoint):
        raise SystemExit("Workstation absolute path remains in portable model")

    comics = sorted((ROOT / "docs" / "comics").glob("*.png"))
    screenshots = sorted((ROOT / "docs" / "screenshots").glob("*.png"))
    examples = sorted((ROOT / "examples").glob("*.png"))
    if len(comics) != 6 or len(screenshots) != 4 or len(examples) != 2:
        raise SystemExit(
            f"Asset count mismatch: comics={len(comics)}, "
            f"screenshots={len(screenshots)}, examples={len(examples)}"
        )
    for path in comics + screenshots + examples:
        with Image.open(path) as opened:
            opened.verify()

    manifest = ROOT / "artifacts_manifest.csv"
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 12:
        raise SystemExit(f"Asset manifest must contain 12 rows, got {len(rows)}")
    for row in rows:
        relative_path = row["path"]
        path = ROOT / relative_path
        if not path.is_file():
            raise SystemExit(f"Manifest path missing: {relative_path}")
        if digest(path) != row["sha256"]:
            raise SystemExit(f"Manifest SHA mismatch: {relative_path}")
        if path.stat().st_size != int(row["bytes"]):
            raise SystemExit(f"Manifest size mismatch: {relative_path}")

    excluded_parts = {".git", ".venv", ".release", "__pycache__", ".pytest_cache"}
    for path in ROOT.rglob("*"):
        relative_parts = set(path.relative_to(ROOT).parts)
        if (
            not path.is_file()
            or relative_parts & excluded_parts
            or path.suffix.lower() in {".png", ".pt", ".pyc", ".lock"}
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise SystemExit(f"Potential secret in {path.relative_to(ROOT)}")

    report = {
        "status": "PASS",
        "portable_model_sha256": MODEL_SHA256,
        "model_source_sha256": checkpoint["provenance"]["source_checkpoint_sha256"],
        "comics": len(comics),
        "screenshots": len(screenshots),
        "examples": len(examples),
        "automatic_dispatch_enabled": False,
        "real_cctv_performance_measured": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
