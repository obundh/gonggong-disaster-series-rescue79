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
COMIC_NAMES = (
    "01_problem.png",
    "02_gap.png",
    "03_proposal.png",
    "04_flow.png",
    "05_method.png",
    "06_validation.png",
    "07_next_steps.png",
)
COMIC_REFERENCE_DOCS = (
    "README.md",
    "docs/COMICS_ALT_TEXT_KO.md",
)
PUBLIC_CORE_DOCS = REQUIRED_DOCS + ("docs/COMICS_ALT_TEXT_KO.md",)
OLD_COMIC_NAMES = (
    "02_solution.png",
    "03_training.png",
    "04_performance.png",
    "05_safe_rollout.png",
    "06_verification.png",
)
COMIC_REFERENCE_PATTERN = re.compile(
    r"(?:docs/comics/)?([0-9]{2}_[A-Za-z0-9_]+\.png)"
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


def comic_references(text: str) -> set[str]:
    return set(COMIC_REFERENCE_PATTERN.findall(text))


def main() -> None:
    for name in REQUIRED_DOCS:
        path = ROOT / name
        if not path.is_file() or path.stat().st_size < 100:
            raise SystemExit(f"Missing or incomplete document: {name}")

    expected_comics = set(COMIC_NAMES)
    for name in COMIC_REFERENCE_DOCS:
        path = ROOT / name
        if not path.is_file():
            raise SystemExit(f"Missing comic reference document: {name}")
        references = comic_references(path.read_text(encoding="utf-8"))
        if references != expected_comics:
            missing = sorted(expected_comics - references)
            unexpected = sorted(references - expected_comics)
            raise SystemExit(
                f"Comic references mismatch in {name}: "
                f"missing={missing}, unexpected={unexpected}"
            )

    for name in PUBLIC_CORE_DOCS:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        for old_name in OLD_COMIC_NAMES:
            if old_name in text:
                raise SystemExit(f"Old comic name remains in {name}: {old_name}")

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
    actual_comic_names = tuple(path.name for path in comics)
    if actual_comic_names != COMIC_NAMES:
        raise SystemExit(
            f"Comic allowlist mismatch: expected={list(COMIC_NAMES)}, "
            f"actual={list(actual_comic_names)}"
        )
    if len(screenshots) != 4 or len(examples) != 2:
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
    if len(rows) != 13:
        raise SystemExit(f"Asset manifest must contain 13 rows, got {len(rows)}")
    expected_manifest_paths = {
        *(f"docs/comics/{name}" for name in COMIC_NAMES),
        *(path.relative_to(ROOT).as_posix() for path in screenshots),
        *(path.relative_to(ROOT).as_posix() for path in examples),
    }
    manifest_paths = [row["path"] for row in rows]
    if len(manifest_paths) != len(set(manifest_paths)):
        raise SystemExit("Asset manifest contains duplicate paths")
    if set(manifest_paths) != expected_manifest_paths:
        missing = sorted(expected_manifest_paths - set(manifest_paths))
        unexpected = sorted(set(manifest_paths) - expected_manifest_paths)
        raise SystemExit(
            f"Asset manifest path mismatch: missing={missing}, "
            f"unexpected={unexpected}"
        )
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
