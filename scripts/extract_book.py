#!/usr/bin/env python3
"""Extract and lightly normalize the Hebrew text layer of Otsar HaKedusha.

The source PDF contains a noisy legacy OCR/text layer. This script preserves
page boundaries and performs only conservative substitutions that improve
readability for analysis without pretending to reconstruct an authoritative
edition.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "book" / "Otzar_HaKedusha_Rabbi_Eliezer_Shlomo_Shick.pdf"
OUT = ROOT / "tmp" / "text" / "chapters"

CHAPTERS = [
    (1, "דמעת העשוקים", 11, 38, 5, 32),
    (2, "משפט העשוקים", 39, 66, 33, 60),
    (3, "ברח מהמלכודת", 67, 92, 61, 86),
    (4, "צא מהבוץ", 93, 120, 87, 114),
    (5, "כבסני מעוני", 121, 140, 115, 134),
    (6, "טהרני מחטאי", 141, 164, 135, 158),
    (7, "שומר הברית", 165, 186, 159, 180),
    (8, "טהרת הברית", 187, 204, 181, 198),
    (9, "טהר עינים", 205, 224, 199, 218),
    (10, "יפה עינים", 225, 246, 219, 240),
    (11, "עינים יפות", 247, 274, 241, 268),
    (12, "שמור עיניך", 275, 298, 269, 292),
    (13, "קדושת העינים", 299, 326, 293, 320),
    (14, "עין בעין", 327, 346, 321, 340),
    (15, "עינים קדושות", 347, 372, 341, 366),
    (16, "מאירת עינים", 373, 417, 367, 410),
]

BIDI = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
JUNK_LINE = re.compile(r"^[\s\W\dITVtmlrxcoJ]+$", re.IGNORECASE)


def clean_page(text: str) -> str:
    text = BIDI.sub("", text)
    text = text.replace("breslevcitvxoJI", "").replace("breslevcity.co.il", "")
    text = text.replace("b re s le v c itv x o J I", "")
    # Common legacy-font OCR substitutions in the running Hebrew typeface.
    text = text.replace("מ1הרא", "מוהרא").replace("מ 1 הרא", "מוהרא")
    text = text.replace("מ^הרא", "מוהרא").replace("מו־הרא", "מוהרא")
    text = text.replace("קז", "ש").replace("עז", "ש")
    text = re.sub(r"(?<=[\u0590-\u05ff])1(?=[\u0590-\u05ff])", "ו", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or JUNK_LINE.fullmatch(line):
            continue
        if len(re.findall(r"[\u0590-\u05ff]", line)) < 2:
            continue
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for number, title, pdf_start, pdf_end, book_start, book_end in CHAPTERS:
        proc = subprocess.run(
            ["pdftotext", "-f", str(pdf_start), "-l", str(pdf_end), "-layout", str(PDF), "-"],
            check=True,
            stdout=subprocess.PIPE,
        )
        raw = proc.stdout.decode("utf-8", errors="replace")
        pages = raw.split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        rendered = [
            f"# פרק {number}: {title}",
            f"PDF: {pdf_start}-{pdf_end} | עמודי הספר: {book_start}-{book_end}",
            "הערה: הטקסט עבר ניקוי OCR שמרני ומשמש לניתוח בלבד.",
            "",
        ]
        for offset, page in enumerate(pages):
            pdf_page = pdf_start + offset
            printed = pdf_page - 7
            printed_label = "שער" if pdf_page == pdf_start else str(printed)
            rendered.extend(
                [
                    f"\n[[PDF_PAGE {pdf_page} | BOOK_PAGE {printed_label}]]",
                    clean_page(page),
                ]
            )
        path = OUT / f"{number:02d}_{title.replace(' ', '_')}.txt"
        path.write_text("\n".join(rendered).strip() + "\n", encoding="utf-8")
        print(f"{path.name}\t{path.stat().st_size}")


if __name__ == "__main__":
    main()
