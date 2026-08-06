#!/usr/bin/env python3
"""Build the KedushaPath 16-card Hebrew print deck."""

from __future__ import annotations

import json
import math
import shutil
import textwrap
import gc
import argparse
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from build_otzar_summary import CHAPTERS


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cards"
PNG = OUT
FRONTS = PNG / "fronts"
BACKS = PNG / "backs"
COVERS = PNG / "covers"
PDF_OUT = OUT / "print"
TMP = ROOT / "tmp" / "kedusha_cards"

COVER_ART = ROOT / "assets" / "art" / "front-cover-art.png"
BACK_ART = ROOT / "assets" / "art" / "back-cover-art.png"

# 10 x 15 cm trim plus 3 mm bleed on each side at 300 dpi.
DPI = 300
TRIM_W = round(10 / 2.54 * DPI)
TRIM_H = round(15 / 2.54 * DPI)
BLEED = round(0.3 / 2.54 * DPI)
W, H = TRIM_W + 2 * BLEED, TRIM_H + 2 * BLEED
SAFE = BLEED + 70

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
# The installed DejaVu Serif lacks Hebrew glyph coverage; use the fully
# Hebrew-capable DejaVu Sans family for display text as well.
FONT_SERIF = FONT_REG
FONT_SERIF_BOLD = FONT_BOLD

GOLD = (236, 194, 101)
PALE_GOLD = (255, 231, 174)
IVORY = (250, 247, 235)
WHITE = (255, 255, 255)
INK = (7, 18, 39)

SLUGS = [
    "dimaat-haashukim", "mishpat-haashukim", "berach-mehamalkodet", "tze-mehabotz",
    "kabseni-meavoni", "tahareni-mechetai", "shomer-habrit", "taharat-habrit",
    "tehor-einayim", "yefe-einayim", "einayim-yafot", "shmor-einecha",
    "kedushat-haeinayim", "ayin-beayin", "einayim-kedoshot", "meirat-einayim",
]

REFLECTIONS = [
    "מהו משפט הייאוש שאחליף היום בבקשת תיקון?",
    "איזה קול מקרב אותי לתורה ולתפילה, ואיזה קול מכניס בלב שנאה?",
    "מהו הטריגר הראשון במלכודת, ומה אעשה במקומו?",
    "איזו אחיזה קבועה תוציא אותי היום מן הבוץ?",
    "עם מי עלי להשלים כדי שתפילתי תצא מלב נקי?",
    "איזה מעשה חסד יוכיח שהטהרה חדרה אל המידות?",
    "איזו מחשבה אחליף מיד בדבר תורה?",
    "איזה הרגל יומי קטן ייתן לי מלכות על הרצון?",
    "מה אבחר לראות היום מעבר ללבוש החיצוני?",
    "איזו נקודה טובה אראה היום באדם אחר?",
    "היכן מתחילה אצלי שרשרת המבט, המחשבה, הרגש והמעשה?",
    "איזה גבול אקבע לפני שאפגוש את הניסיון?",
    "אילו תמונות מחממות בי אמונה ואילו מקררות אותה?",
    "באיזה פרט קטן ראיתי היום השגחה?",
    "איזה שכל וחיות אגלה בדבר הפשוט שלפני?",
    "איזה מקור תוכן אסיר כדי לפנות מקום לאור?",
]

PALETTES = [
    ((5, 25, 68), (50, 72, 154), (236, 194, 101)),
    ((5, 34, 60), (17, 105, 117), (236, 205, 117)),
    ((27, 10, 68), (98, 45, 140), (225, 188, 255)),
    ((12, 32, 75), (43, 108, 174), (247, 225, 164)),
]


@lru_cache(maxsize=96)
def font(size: int, bold: bool = False, serif: bool = False) -> ImageFont.FreeTypeFont:
    if serif:
        path = FONT_SERIF_BOLD if bold else FONT_SERIF
    else:
        path = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, size=size, layout_engine=ImageFont.Layout.RAQM)


def cover_crop(path: Path, size=(W, H)) -> Image.Image:
    image = Image.open(path).convert("RGB")
    src_ratio = image.width / image.height
    dst_ratio = size[0] / size[1]
    if src_ratio > dst_ratio:
        new_w = round(image.height * dst_ratio)
        left = (image.width - new_w) // 2
        image = image.crop((left, 0, left + new_w, image.height))
    else:
        new_h = round(image.width / dst_ratio)
        top = (image.height - new_h) // 2
        image = image.crop((0, top, image.width, top + new_h))
    return image.resize(size, Image.Resampling.LANCZOS)


def vertical_gradient(size, top, bottom, alpha=255):
    grad = Image.new("RGBA", (1, size[1]))
    px = grad.load()
    for y in range(size[1]):
        t = y / max(1, size[1] - 1)
        col = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3)) + (alpha,)
        px[0, y] = col
    return grad.resize(size, Image.Resampling.BILINEAR)


def rounded_panel(base, box, fill, outline=GOLD, width=3, radius=34, glow=False):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if glow:
        glow_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        gd.rounded_rectangle(box, radius=radius, outline=outline + (110,), width=10)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(16))
        base.alpha_composite(glow_layer)
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline + (225,), width=width)
    base.alpha_composite(layer)


def text_width(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt, direction="rtl")
    return box[2] - box[0]


def wrap_rtl(draw, text, fnt, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if text_width(draw, candidate, fnt) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_lines(draw, text, max_width, max_lines, start_size, min_size=28, bold=False, serif=False):
    for size in range(start_size, min_size - 1, -2):
        fnt = font(size, bold=bold, serif=serif)
        lines = wrap_rtl(draw, text, fnt, max_width)
        if len(lines) <= max_lines:
            return fnt, lines
    fnt = font(min_size, bold=bold, serif=serif)
    return fnt, wrap_rtl(draw, text, fnt, max_width)[:max_lines]


def draw_centered_lines(draw, lines, fnt, center_x, start_y, fill, spacing=1.25, stroke=0, stroke_fill=None):
    line_h = round(fnt.size * spacing)
    for i, line in enumerate(lines):
        draw.text(
            (center_x, start_y + i * line_h), line, font=fnt, fill=fill,
            anchor="ma", direction="rtl", stroke_width=stroke, stroke_fill=stroke_fill,
        )
    return start_y + len(lines) * line_h


def draw_right_lines(draw, lines, fnt, right_x, start_y, fill, spacing=1.25):
    line_h = round(fnt.size * spacing)
    for i, line in enumerate(lines):
        draw.text((right_x, start_y + i * line_h), line, font=fnt, fill=fill, anchor="ra", direction="rtl")
    return start_y + len(lines) * line_h


def draw_rule(draw, y, x1=SAFE, x2=W-SAFE, color=GOLD, width=3):
    draw.line((x1, y, x2, y), fill=color, width=width)
    draw.ellipse((W//2-7, y-7, W//2+7, y+7), fill=PALE_GOLD)


def bidi_number_ranges(text: str) -> str:
    """Keep numeric page ranges in natural left-to-right order inside RTL text."""
    return re.sub(
        r"(\d+)[–-](\d+)",
        lambda m: "\u202a" + m.group(1) + "-" + m.group(2) + "\u202c",
        text,
    )


def draw_radiant_icon(base: Image.Image, idx: int, center, radius=120):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=GOLD + (90,))
    glow = glow.filter(ImageFilter.GaussianBlur(45))
    base.alpha_composite(glow)

    for n in range(16):
        a = 2 * math.pi * n / 16 - math.pi / 2
        r1, r2 = radius + 20, radius + 52 + (10 if n == idx-1 else 0)
        x1, y1 = cx + math.cos(a)*r1, cy + math.sin(a)*r1
        x2, y2 = cx + math.cos(a)*r2, cy + math.sin(a)*r2
        d.line((x1, y1, x2, y2), fill=PALE_GOLD + ((230 if n == idx-1 else 105),), width=(7 if n == idx-1 else 3))
    d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(7, 22, 55, 220), outline=GOLD + (255,), width=6)
    d.ellipse((cx-radius+17, cy-radius+17, cx+radius-17, cy+radius-17), outline=PALE_GOLD + (150,), width=2)

    c = GOLD + (255,)
    w = 8
    r = radius * 0.58
    if idx == 1:  # tear
        pts = [(cx, cy-r), (cx-r*.48, cy+r*.18), (cx, cy+r*.67), (cx+r*.48, cy+r*.18)]
        d.line(pts + [pts[0]], fill=c, width=w, joint="curve")
    elif idx == 2:  # scales
        d.line((cx, cy-r*.68, cx, cy+r*.56), fill=c, width=w)
        d.line((cx-r*.62, cy-r*.32, cx+r*.62, cy-r*.32), fill=c, width=w)
        for s in (-1, 1):
            sx = cx+s*r*.48
            d.line((sx, cy-r*.30, sx-s*r*.16, cy+r*.17), fill=c, width=5)
            d.arc((sx-r*.30, cy, sx+r*.30, cy+r*.42), 0, 180, fill=c, width=6)
        d.line((cx-r*.33, cy+r*.58, cx+r*.33, cy+r*.58), fill=c, width=w)
    elif idx == 3:  # open gate
        d.arc((cx-r*.62, cy-r*.68, cx+r*.62, cy+r*.56), 180, 360, fill=c, width=w)
        d.line((cx-r*.62, cy, cx-r*.62, cy+r*.62), fill=c, width=w)
        d.line((cx+r*.62, cy, cx+r*.62, cy+r*.62), fill=c, width=w)
        d.line((cx-r*.2, cy+r*.62, cx, cy+r*.18, cx+r*.2, cy+r*.62), fill=c, width=7)
    elif idx == 4:  # rising path
        for n in range(4):
            y = cy+r*.58-n*r*.37
            width2 = r*(.62-n*.12)
            d.line((cx-width2, y, cx+width2, y), fill=c, width=7)
        d.line((cx, cy+r*.55, cx, cy-r*.62), fill=PALE_GOLD+(255,), width=4)
    elif idx == 5:  # water / washing
        for n in range(3):
            y = cy-r*.28+n*r*.30
            d.arc((cx-r*.72, y-r*.16, cx, y+r*.16), 0, 180, fill=c, width=6)
            d.arc((cx, y-r*.16, cx+r*.72, y+r*.16), 180, 360, fill=c, width=6)
    elif idx == 6:  # cleansing flame
        pts = [(cx, cy-r*.72), (cx-r*.46, cy+r*.12), (cx-r*.22, cy+r*.64), (cx, cy+r*.40), (cx+r*.28, cy+r*.62), (cx+r*.5, cy+r*.08)]
        d.line(pts+[pts[0]], fill=c, width=w, joint="curve")
        d.arc((cx-r*.23, cy, cx+r*.23, cy+r*.56), 0, 180, fill=PALE_GOLD+(255,), width=6)
    elif idx == 7:  # shield
        pts = [(cx, cy-r*.65), (cx-r*.55, cy-r*.36), (cx-r*.44, cy+r*.33), (cx, cy+r*.67), (cx+r*.44, cy+r*.33), (cx+r*.55, cy-r*.36)]
        d.line(pts+[pts[0]], fill=c, width=w, joint="curve")
        d.line((cx-r*.28, cy, cx-r*.05, cy+r*.25, cx+r*.34, cy-r*.28), fill=PALE_GOLD+(255,), width=7)
    elif idx == 8:  # crown
        pts = [(cx-r*.66, cy+r*.37), (cx-r*.50, cy-r*.42), (cx-r*.10, cy+r*.02), (cx, cy-r*.64), (cx+r*.16, cy+r*.02), (cx+r*.52, cy-r*.42), (cx+r*.66, cy+r*.37)]
        d.line(pts, fill=c, width=w, joint="curve")
        d.line((cx-r*.66, cy+r*.44, cx+r*.66, cy+r*.44), fill=c, width=w)
    else:  # eye family, evolving from protected to radiant
        d.arc((cx-r*.72, cy-r*.42, cx+r*.72, cy+r*.42), 200, 340, fill=c, width=w)
        d.arc((cx-r*.72, cy-r*.42, cx+r*.72, cy+r*.42), 20, 160, fill=c, width=w)
        pupil = r*(.18 + .012*(idx-9))
        d.ellipse((cx-pupil, cy-pupil, cx+pupil, cy+pupil), fill=PALE_GOLD+(255,))
        if idx >= 13:
            for n in range(8):
                a = n*math.pi/4
                d.line((cx+math.cos(a)*r*.82, cy+math.sin(a)*r*.56,
                        cx+math.cos(a)*r*1.05, cy+math.sin(a)*r*.78), fill=c, width=4)
        if idx == 15:
            d.line((cx, cy-r*.75, cx, cy+r*.75), fill=(255,255,255,170), width=3)
        if idx == 16:
            d.ellipse((cx-r*.10, cy-r*.10, cx+r*.10, cy+r*.10), fill=WHITE+(255,))
    base.alpha_composite(layer)


def tint_background(source: Image.Image, chapter_index: int) -> Image.Image:
    group = (chapter_index - 1) // 4
    top, bottom, accent = PALETTES[group]
    image = source.copy().convert("RGBA")
    image = ImageEnhance.Color(image).enhance(0.82 + group * .08)
    image = ImageEnhance.Contrast(image).enhance(1.05)
    overlay = vertical_gradient(image.size, top, bottom, alpha=155)
    image.alpha_composite(overlay)
    dark = Image.new("RGBA", image.size, (0, 6, 20, 72))
    image.alpha_composite(dark)
    return image


def draw_header(draw, n, side="חזית"):
    f = font(30, bold=True)
    draw.text((SAFE, 70), f"{n:02d} / 16", font=f, fill=PALE_GOLD, anchor="la", direction="ltr")
    draw.text((W-SAFE, 70), f"אוצר הקדושה • {side}", font=f, fill=IVORY, anchor="ra", direction="rtl")
    draw_rule(draw, 122)


def make_front(chapter, idx, source):
    base = tint_background(source, idx)
    draw = ImageDraw.Draw(base)
    draw_header(draw, idx, "קלף")

    title_panel = (SAFE-15, 155, W-SAFE+15, 575)
    rounded_panel(base, title_panel, (3, 13, 35, 205), glow=True)
    draw = ImageDraw.Draw(base)
    draw.text((W//2, 180), "שַׁעַר", font=font(32, bold=True), fill=GOLD, anchor="ma", direction="rtl")
    title_font, title_lines = fit_lines(draw, chapter["title"], W-2*SAFE-80, 2, 76, 54, bold=True, serif=True)
    draw_centered_lines(draw, title_lines, title_font, W//2, 225, WHITE, spacing=1.18, stroke=2, stroke_fill=(2,8,22))
    draw_radiant_icon(base, idx, (W//2, 442), radius=90)

    core_box = (SAFE-15, 620, W-SAFE+15, 1075)
    rounded_panel(base, core_box, (4, 17, 43, 220))
    draw = ImageDraw.Draw(base)
    draw.text((W-SAFE-38, 660), "לֵב הַקֶּלֶף", font=font(34, bold=True), fill=PALE_GOLD, anchor="ra", direction="rtl")
    fnt, lines = fit_lines(draw, chapter["core"], W-2*SAFE-95, 7, 45, 34, bold=False)
    draw_centered_lines(draw, lines, fnt, W//2, 730, IVORY, spacing=1.32)

    quote_box = (SAFE-15, 1120, W-SAFE+15, 1528)
    rounded_panel(base, quote_box, (31, 18, 48, 215), outline=(220, 183, 245))
    draw = ImageDraw.Draw(base)
    draw.text((W//2, 1155), "מִשְׁפַּט אוֹר", font=font(31, bold=True), fill=(231, 207, 255), anchor="ma", direction="rtl")
    quote = "״" + chapter["anthology"][0][0] + "״"
    qfont, qlines = fit_lines(draw, quote, W-2*SAFE-100, 5, 43, 32, bold=True, serif=True)
    draw_centered_lines(draw, qlines, qfont, W//2, 1225, WHITE, spacing=1.34)
    draw.text((W//2, 1468), bidi_number_ranges(chapter["anthology"][0][1]), font=font(25), fill=PALE_GOLD, anchor="ma", direction="rtl")

    draw_rule(draw, 1594)
    draw.text((W//2, 1633), bidi_number_ranges(f"מראה מקום בספר: {chapter['pages']}"), font=font(27, bold=True), fill=IVORY, anchor="ma", direction="rtl")
    draw.text((W//2, 1694), "על פי ספר אוצר הקדושה • רבי אליעזר שלמה שיק", font=font(23), fill=(218,225,240), anchor="ma", direction="rtl")
    draw.text((W//2, 1745), "KedushaPath • KP", font=font(22, bold=True), fill=GOLD, anchor="ma", direction="ltr")
    return base.convert("RGB")


def make_back(chapter, idx, source):
    base = source.copy().convert("RGBA")
    base.alpha_composite(vertical_gradient(base.size, (3, 15, 43), (26, 10, 54), alpha=130))
    base.alpha_composite(Image.new("RGBA", base.size, (1, 8, 25, 105)))
    draw = ImageDraw.Draw(base)
    draw_header(draw, idx, "עבודה")

    rounded_panel(base, (SAFE-15, 155, W-SAFE+15, 340), (3, 15, 40, 225), glow=True)
    draw = ImageDraw.Draw(base)
    draw.text((W//2, 190), chapter["title"], font=font(54, bold=True, serif=True), fill=WHITE, anchor="ma", direction="rtl", stroke_width=2, stroke_fill=(0,0,0))
    draw.text((W//2, 270), "הֲלָכָה לְמַעֲשֶׂה", font=font(31, bold=True), fill=PALE_GOLD, anchor="ma", direction="rtl")

    panel = (SAFE-15, 385, W-SAFE+15, 1195)
    rounded_panel(base, panel, (3, 16, 44, 226))
    draw = ImageDraw.Draw(base)
    y = 445
    bullet_font = font(37, bold=False)
    bullet_max = W - 2*SAFE - 155
    for n, item in enumerate(chapter["practice"], 1):
        lines = wrap_rtl(draw, item, bullet_font, bullet_max)
        if len(lines) > 3:
            bf, lines = fit_lines(draw, item, bullet_max, 3, 37, 31)
        else:
            bf = bullet_font
        draw.ellipse((W-SAFE-65, y+10, W-SAFE-41, y+34), fill=GOLD)
        draw.text((W-SAFE-53, y+22), str(n), font=font(19, bold=True), fill=INK, anchor="mm")
        draw_right_lines(draw, lines, bf, W-SAFE-93, y, IVORY, spacing=1.28)
        y += max(148, len(lines)*round(bf.size*1.28)+40)

    rounded_panel(base, (SAFE-15, 1240, W-SAFE+15, 1535), (36, 20, 57, 226), outline=(220, 183, 245))
    draw = ImageDraw.Draw(base)
    draw.text((W-SAFE-35, 1275), "שְׁאֵלַת דֶּרֶךְ", font=font(30, bold=True), fill=(233, 210, 255), anchor="ra", direction="rtl")
    rf, rlines = fit_lines(draw, REFLECTIONS[idx-1], W-2*SAFE-95, 4, 41, 32, bold=True, serif=True)
    draw_centered_lines(draw, rlines, rf, W//2, 1338, WHITE, spacing=1.32)

    draw_rule(draw, 1594)
    closing = chapter["anthology"][-1][0]
    cf, clines = fit_lines(draw, closing, W-2*SAFE-100, 2, 29, 23, bold=True)
    draw_centered_lines(draw, clines, cf, W//2, 1623, PALE_GOLD, spacing=1.25)
    draw.text((W//2, 1732), "אוצר הקדושה • מסע של תשובה מתמשכת", font=font(22), fill=(220,228,242), anchor="ma", direction="rtl")
    return base.convert("RGB")


def make_cover_front(source):
    base = source.copy().convert("RGBA")
    base.alpha_composite(vertical_gradient(base.size, (3,12,35), (6,15,42), alpha=75))
    rounded_panel(base, (SAFE-20, 105, W-SAFE+20, 520), (2, 12, 35, 205), glow=True)
    rounded_panel(base, (SAFE+25, 1405, W-SAFE-25, 1725), (3, 15, 40, 218))
    draw = ImageDraw.Draw(base)
    draw.text((W//2, 150), "KedushaPath • KP", font=font(31, bold=True), fill=GOLD, anchor="ma")
    draw.text((W//2, 222), "אוֹצַר הַקְּדֻשָּׁה", font=font(72, bold=True, serif=True), fill=WHITE, anchor="ma", direction="rtl", stroke_width=2, stroke_fill=(0,0,0))
    draw.text((W//2, 335), "סדרת 16 קלפים", font=font(45, bold=True), fill=PALE_GOLD, anchor="ma", direction="rtl")
    draw.text((W//2, 410), "תשובה • טהרה • ברית • עיניים מאירות", font=font(27, bold=True), fill=IVORY, anchor="ma", direction="rtl")
    draw.text((W//2, 1460), "מִן הַנְּפִילָה אֶל הָאוֹר", font=font(43, bold=True, serif=True), fill=WHITE, anchor="ma", direction="rtl")
    draw.text((W//2, 1540), "קלף אחד לכל פרק בספר", font=font(30, bold=True), fill=PALE_GOLD, anchor="ma", direction="rtl")
    draw.text((W//2, 1605), "על פי ספרו של רבי אליעזר שלמה שיק", font=font(26), fill=IVORY, anchor="ma", direction="rtl")
    draw.text((W//2, 1662), "מהדורת הדפסה • 10×15 ס״מ", font=font(22), fill=(219,226,241), anchor="ma", direction="rtl")
    return base.convert("RGB")


def make_cover_back(source):
    base = source.copy().convert("RGBA")
    base.alpha_composite(Image.new("RGBA", base.size, (1, 9, 28, 118)))
    rounded_panel(base, (SAFE-15, 110, W-SAFE+15, 1625), (2, 14, 40, 225), glow=True)
    draw = ImageDraw.Draw(base)
    draw.text((W//2, 160), "16 שְׁעָרִים • מַסָּע אֶחָד", font=font(47, bold=True, serif=True), fill=WHITE, anchor="ma", direction="rtl")
    draw_rule(draw, 250, SAFE+35, W-SAFE-35)
    stages = [
        ("01–04", "יציאה מן הנפילה והמלכודת"),
        ("05–08", "טהרה, תיקון הברית ובניית סדר"),
        ("09–12", "שמירת העיניים ועין טובה"),
        ("13–16", "ראיית החיות, ההשגחה והאור"),
    ]
    y = 310
    for num, title in stages:
        draw.text((W-SAFE-55, y), title, font=font(34, bold=True), fill=IVORY, anchor="ra", direction="rtl")
        draw.text((SAFE+55, y), num, font=font(27, bold=True), fill=GOLD, anchor="la")
        y += 118
    draw_rule(draw, 800, SAFE+35, W-SAFE-35)
    verse = "״לֵב טָהוֹר בְּרָא לִי אֱלֹהִים;\nוְרוּחַ נָכוֹן חַדֵּשׁ בְּקִרְבִּי״"
    for i, line in enumerate(verse.splitlines()):
        draw.text((W//2, 855+i*63), line, font=font(35, bold=True, serif=True), fill=PALE_GOLD, anchor="ma", direction="rtl")
    draw.text((W//2, 1000), "תהלים נא, יב", font=font(23), fill=IVORY, anchor="ma", direction="rtl")
    draw_rule(draw, 1065, SAFE+35, W-SAFE-35)
    credits = [
        "מקור: אוצר הקדושה — רבי אליעזר שלמה שיק",
        "עריכה ועיצוב: Cyber Shamanic (CySh)",
        "לאון יעקובוב (AnLoMinus)",
        "github.com/Cyber-Shamanic • github.com/AnLoMinus",
        "linkedin.com/in/anlominus",
        "מהדורה 1.0.0 • כ״ג באב ה׳תשפ״ו • 6.8.2026 • 02:28",
    ]
    y = 1115
    for line in credits:
        f = font(24 if "github" not in line and "linkedin" not in line else 21, bold=(line.startswith("מקור") or line.startswith("עריכה")))
        direction = "ltr" if line.startswith("github") or line.startswith("linkedin") else "rtl"
        draw.text((W//2, y), line, font=f, fill=IVORY, anchor="ma", direction=direction)
        y += 56
    draw.text((W//2, 1485), "מספר המידות", font=font(27, bold=True), fill=GOLD, anchor="ma", direction="rtl")
    draw.text((W//2, 1535), "16 קלפים • 32 צדדים • 64 פעולות • 128 ליקוטים במקור", font=font(22, bold=True), fill=WHITE, anchor="ma", direction="rtl")
    return base.convert("RGB")


def crop_trim(path: Path, dst: Path):
    image = Image.open(path)
    image.crop((BLEED, BLEED, BLEED+TRIM_W, BLEED+TRIM_H)).convert("RGB").save(
        dst, dpi=(DPI,DPI), quality=92, subsampling=0
    )


def valid_png(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 500_000:
        return False
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def build_card_pdf(pairs, out_path: Path):
    c = canvas.Canvas(str(out_path), pagesize=(10*cm, 15*cm), pageCompression=1)
    for image_path in pairs:
        c.drawImage(str(image_path), 0, 0, width=10*cm, height=15*cm, preserveAspectRatio=False, mask='auto')
        c.showPage()
    c.setTitle("KedushaPath - 16 Cards")
    c.setAuthor("Cyber Shamanic / AnLoMinus")
    c.save()


def crop_marks(c, x, y, w, h, mark=0.35*cm, gap=0.08*cm):
    c.setStrokeColorRGB(.12,.12,.12)
    c.setLineWidth(.25)
    for px, py, sx, sy in [
        (x, y, -1, 0), (x, y, 0, -1), (x+w, y, 1, 0), (x+w, y, 0, -1),
        (x, y+h, -1, 0), (x, y+h, 0, 1), (x+w, y+h, 1, 0), (x+w, y+h, 0, 1),
    ]:
        if sx:
            c.line(px+sx*gap, py, px+sx*(gap+mark), py)
        else:
            c.line(px, py+sy*gap, px, py+sy*(gap+mark))


def build_a4_duplex(fronts, backs, cover_front, cover_back, out_path):
    page_w, page_h = A4
    card_w, card_h = 10*cm, 15*cm
    x1 = (page_w - 2*card_w) / 2
    x2 = x1 + card_w
    y = (page_h - card_h) / 2
    c = canvas.Canvas(str(out_path), pagesize=A4, pageCompression=1)
    sheets = [(cover_front, cover_front, cover_back, cover_back)]
    for i in range(0, 16, 2):
        sheets.append((fronts[i], fronts[i+1], backs[i], backs[i+1]))
    for left_f, right_f, left_b, right_b in sheets:
        for p, x in ((left_f, x1), (right_f, x2)):
            c.drawImage(str(p), x, y, width=card_w, height=card_h, preserveAspectRatio=False)
            crop_marks(c, x, y, card_w, card_h)
        c.showPage()
        # Backs are intentionally in the same positions; duplex print with long-edge flip.
        for p, x in ((left_b, x1), (right_b, x2)):
            c.drawImage(str(p), x, y, width=card_w, height=card_h, preserveAspectRatio=False)
            crop_marks(c, x, y, card_w, card_h)
        c.showPage()
    c.setTitle("KedushaPath - A4 Duplex Print Sheets")
    c.setAuthor("Cyber Shamanic / AnLoMinus")
    c.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=16)
    parser.add_argument("--png-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--sides", choices=("all", "front", "back"), default="all")
    args = parser.parse_args()
    for d in (FRONTS, BACKS, COVERS, PDF_OUT, TMP):
        d.mkdir(parents=True, exist_ok=True)
    cover_src = cover_crop(COVER_ART)
    back_src = cover_crop(BACK_ART)

    cover_front = COVERS / "cover-front.png"
    cover_back = COVERS / "cover-back.png"
    if (args.force and args.start == 1 and args.sides == "all") or not valid_png(cover_front):
        make_cover_front(cover_src).save(cover_front, dpi=(DPI,DPI), optimize=True)
    if (args.force and args.start == 1 and args.sides == "all") or not valid_png(cover_back):
        make_cover_back(back_src).save(cover_back, dpi=(DPI,DPI), optimize=True)

    front_paths, back_paths = [], []
    for idx, chapter in enumerate(CHAPTERS, 1):
        front = FRONTS / f"{idx:02d}-{SLUGS[idx-1]}-front.png"
        back = BACKS / f"{idx:02d}-{SLUGS[idx-1]}-back.png"
        if args.sides in ("all", "front") and args.start <= idx <= args.end and (args.force or not valid_png(front)):
            front_image = make_front(chapter, idx, cover_src)
            front_image.save(front, dpi=(DPI,DPI), optimize=True)
            del front_image
        if args.sides in ("all", "back") and args.start <= idx <= args.end and (args.force or not valid_png(back)):
            back_image = make_back(chapter, idx, back_src)
            back_image.save(back, dpi=(DPI,DPI), optimize=True)
            del back_image
        front_paths.append(front)
        back_paths.append(back)
        gc.collect()
        if args.start <= idx <= args.end:
            print(f"built {idx:02d}/16", flush=True)

    if args.png_only:
        return

    trim_dir = TMP / "trim"
    trim_dir.mkdir(parents=True, exist_ok=True)
    trimmed = {}
    for p in [cover_front, cover_back] + front_paths + back_paths:
        dst = trim_dir / (p.stem + ".jpg")
        crop_trim(p, dst)
        trimmed[p] = dst

    sequence = [trimmed[cover_front]]
    for f, b in zip(front_paths, back_paths):
        sequence.extend([trimmed[f], trimmed[b]])
    sequence.append(trimmed[cover_back])
    build_card_pdf(sequence, PDF_OUT / "KedushaPath_16_Cards_Print_10x15cm.pdf")
    build_a4_duplex(
        [trimmed[p] for p in front_paths], [trimmed[p] for p in back_paths],
        trimmed[cover_front], trimmed[cover_back],
        PDF_OUT / "KedushaPath_16_Cards_A4_Duplex.pdf",
    )

    manifest = {
        "project": "KedushaPath (KP)",
        "version": "1.0.0",
        "cards": 16,
        "sides": 32,
        "covers": 2,
        "trim_cm": [10, 15],
        "bleed_mm": 3,
        "dpi": DPI,
        "source": "אוצר הקדושה — רבי אליעזר שלמה שיק",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "fronts": len(front_paths), "backs": len(back_paths),
        "covers": [str(cover_front), str(cover_back)],
        "pdfs": [
            str(PDF_OUT / "KedushaPath_16_Cards_Print_10x15cm.pdf"),
            str(PDF_OUT / "KedushaPath_16_Cards_A4_Duplex.pdf"),
        ],
        "size": [W, H], "trim": [TRIM_W, TRIM_H]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
