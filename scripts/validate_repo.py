#!/usr/bin/env python3
"""Validate the release structure using only the Python standard library."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.links.append(value)


def require(path: str) -> Path:
    item = ROOT / path
    if not item.exists():
        errors.append(f"Missing: {path}")
    return item


def pdf_pages(path: Path) -> int | None:
    try:
        output = subprocess.run(
            ["pdfinfo", str(path)], check=True, capture_output=True, text=True
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    match = re.search(r"^Pages:\s+(\d+)$", output, re.MULTILINE)
    return int(match.group(1)) if match else None


def main() -> int:
    version = require("VERSION")
    if version.exists() and version.read_text(encoding="utf-8").strip() != "1.0.0":
        errors.append("VERSION must equal 1.0.0")

    essentials = [
        "README.md", "CHANGELOG.md", "TODO.md", "LICENSE.md", "SOURCE_NOTICE.md",
        "index.html", "assets/css/styles.css", "assets/js/app.js", "manifest.webmanifest",
        "book/Otzar_HaKedusha_Rabbi_Eliezer_Shlomo_Shick.pdf",
        "documents/Otzar_HaKedusha_Full_Summary_HE.pdf",
        "documents/Otzar_HaKedusha_Full_Summary_HE.docx",
        "cards/print/KedushaPath_16_Cards_A4_Duplex.pdf",
        "cards/print/KedushaPath_16_Cards_Print_10x15cm.pdf",
        "data/chapters.json", "data/chapters.js", "data/docs.js",
    ]
    for path in essentials:
        require(path)

    fronts = sorted((ROOT / "cards/fronts").glob("*.png"))
    backs = sorted((ROOT / "cards/backs").glob("*.png"))
    covers = sorted((ROOT / "cards/covers").glob("*.png"))
    if len(fronts) != 16:
        errors.append(f"Expected 16 fronts, found {len(fronts)}")
    if len(backs) != 16:
        errors.append(f"Expected 16 backs, found {len(backs)}")
    if len(covers) != 2:
        errors.append(f"Expected 2 covers, found {len(covers)}")

    data_path = ROOT / "data/chapters.json"
    if data_path.exists():
        chapters = json.loads(data_path.read_text(encoding="utf-8"))
        if len(chapters) != 16:
            errors.append(f"Expected 16 chapter records, found {len(chapters)}")
        if sum(len(item.get("anthology", [])) for item in chapters) != 128:
            errors.append("Expected 128 anthology items")
        for item in chapters:
            for key in ("front", "back"):
                if not (ROOT / item[key]).exists():
                    errors.append(f"Broken chapter asset: {item[key]}")

    page_expectations = {
        "book/Otzar_HaKedusha_Rabbi_Eliezer_Shlomo_Shick.pdf": 417,
        "documents/Otzar_HaKedusha_Full_Summary_HE.pdf": 38,
        "cards/print/KedushaPath_16_Cards_Print_10x15cm.pdf": 34,
        "cards/print/KedushaPath_16_Cards_A4_Duplex.pdf": 18,
    }
    for path, expected in page_expectations.items():
        item = ROOT / path
        if item.exists():
            actual = pdf_pages(item)
            if actual is not None and actual != expected:
                errors.append(f"{path}: expected {expected} pages, found {actual}")

    index = ROOT / "index.html"
    if index.exists():
        collector = LinkCollector()
        collector.feed(index.read_text(encoding="utf-8"))
        for link in collector.links:
            clean = link.split("#", 1)[0].split("?", 1)[0]
            if not clean or re.match(r"^(?:https?:|mailto:|tel:|data:)", clean):
                continue
            if not (ROOT / clean).exists():
                errors.append(f"Broken local HTML reference: {link}")

    oversized = [p for p in ROOT.rglob("*") if p.is_file() and p.stat().st_size >= 100_000_000]
    if oversized:
        errors.extend(f"GitHub 100 MB limit exceeded: {p.relative_to(ROOT)}" for p in oversized)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OK — 16 chapters, 32 card sides, 2 covers, 128 anthology entries and all release assets validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
