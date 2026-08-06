#!/usr/bin/env python3
"""Create deterministic SHA-256 checksums for release assets."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "SHA256SUMS.txt"
INCLUDED = ("book", "documents", "cards", "assets/art")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    files = sorted(
        path for directory in INCLUDED for path in (ROOT / directory).rglob("*") if path.is_file()
    )
    lines = [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in files]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} checksums to {OUTPUT.name}")


if __name__ == "__main__":
    main()
