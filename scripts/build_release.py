"""Build a deterministic public source bundle and checksum manifest."""

from __future__ import annotations

import hashlib
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / ".release"
VERSION = "0.2.0"
ARCHIVE_NAME = f"gonggong-disaster-series-rescue79-v{VERSION}.zip"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def tracked_files() -> list[Path]:
    """Use Git's reviewed allowlist; never package arbitrary local files."""

    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    names = [name for name in completed.stdout.split(b"\0") if name]
    files: list[Path] = []
    for raw_name in names:
        relative = Path(raw_name.decode("utf-8"))
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"Tracked release file is missing: {relative}")
        files.append(path)
    if not files:
        raise SystemExit("No tracked files. Stage the reviewed release scope first.")
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive = OUTPUT_DIR / ARCHIVE_NAME
    files = tracked_files()
    timestamp = (2026, 8, 12, 0, 0, 0)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            relative = Path("gonggong-disaster-series-rescue79") / path.relative_to(ROOT)
            info = zipfile.ZipInfo(relative.as_posix(), timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    model = ROOT / "models" / "rescue79-hard4-portable-v1.pt"
    checksum_file = OUTPUT_DIR / "SHA256SUMS.txt"
    checksum_file.write_text(
        f"{digest(archive)}  {archive.name}\n"
        f"{digest(model)}  {model.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"archive={archive}")
    print(f"archive_sha256={digest(archive)}")
    print(f"archive_bytes={archive.stat().st_size}")
    print(f"file_count={len(files)}")
    print(f"checksums={checksum_file}")


if __name__ == "__main__":
    main()
