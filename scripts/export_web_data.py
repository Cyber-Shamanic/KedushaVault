#!/usr/bin/env python3
"""Export the editorial chapter model as stable JSON for the static site."""

from __future__ import annotations

import json
from pathlib import Path

from build_otzar_summary import CHAPTERS

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "chapters.json"
OUTPUT_JS = ROOT / "data" / "chapters.js"
DOCS_JS = ROOT / "data" / "docs.js"

SLUGS = [
    "dimaat-haashukim", "mishpat-haashukim", "berach-mehamalkodet", "tze-mehabotz",
    "kabseni-meavoni", "tahareni-mechetai", "shomer-habrit", "taharat-habrit",
    "tehor-einayim", "yefe-einayim", "einayim-yafot", "shmor-einecha",
    "kedushat-haeinayim", "ayin-beayin", "einayim-kedoshot", "meirat-einayim",
]


def main() -> None:
    exported = []
    for chapter, slug in zip(CHAPTERS, SLUGS, strict=True):
        item = dict(chapter)
        item.update(
            slug=slug,
            group="recovery" if chapter["n"] <= 8 else "eyes",
            front=f"cards/fronts/{chapter['n']:02d}-{slug}-front.png",
            back=f"cards/backs/{chapter['n']:02d}-{slug}-back.png",
        )
        exported.append(item)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(exported, ensure_ascii=False, indent=2)
    OUTPUT.write_text(payload + "\n", encoding="utf-8")
    OUTPUT_JS.write_text("window.KEDUSHA_CHAPTERS = " + payload + ";\n", encoding="utf-8")
    docs = {
        name: (ROOT / name).read_text(encoding="utf-8")
        for name in ("CHANGELOG.md", "TODO.md")
        if (ROOT / name).exists()
    }
    DOCS_JS.write_text(
        "window.KEDUSHA_DOCS = " + json.dumps(docs, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Exported {len(exported)} chapters and {len(docs)} embedded documents")


if __name__ == "__main__":
    main()
