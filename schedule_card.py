"""Schedule card: day groups and rows with time, status, category, members, title and a member sticker.

Special follows use the brand accent (a vertical bar and a tinted row), as the panel marks a selected item.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageOps

from .card_kit import (BRAND, BRAND_SOFT, Card, ERROR, ERROR_BG, Fonts, INK, LINE, MUTED, PAGE, PRIMARY, SUCCESS,
                       SUCCESS_BG, SURFACE, TINTS, Style, draw_chip, draw_mark, draw_text, footer, measure, px, wrap)

# Members' official colors; others take a panel avatar tint chosen by name.
MEMBER_COLORS = {"嘉然": "#e799b0", "贝拉": "#db7d74", "乃琳": "#576690", "向晚": "#9ac8e2", "珈乐": "#b8a6d9"}
WEEKDAYS = "一二三四五六日"


def shade(color: str, factor: float) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f"#{round(r * factor):02x}{round(g * factor):02x}{round(b * factor):02x}"


def tint(color: str, amount: float) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    m = lambda c: round(c + (255 - c) * amount)
    return f"#{m(r):02x}{m(g):02x}{m(b):02x}"


def member_style(name: str) -> tuple[str, str]:
    """(text, background) for a member chip, keeping text readable on its tint."""
    if name in MEMBER_COLORS:
        base = MEMBER_COLORS[name]
        return (base if name == "乃琳" else shade(base, 0.62)), tint(base, 0.84)
    background, text = TINTS[sum(map(ord, name)) % len(TINTS)]
    return text, background


@dataclass
class Entry:
    start: datetime
    title: str
    category: str = ""
    members: list[str] = field(default_factory=list)
    highlight: bool = False
    cancelled: bool = False
    live_now: bool = False


@dataclass
class Day:
    day: date
    entries: list[Entry]
    today: bool = False


def render_schedule(title: str, subtitle: str, days: list[Day], fonts: Fonts, *,
                    stickers: dict[str, list[Path]], source: str, compact: bool = False) -> bytes:
    card = Card(fonts)
    chooser = random.Random()
    used: set[Path] = set()

    def sticker(members: list[str]) -> Image.Image | None:
        # Each row draws its own sticker; within one card a member's stickers do not repeat until used up.
        pool = [path for name in members for path in stickers.get(name, [])]
        fresh = [path for path in pool if path not in used] or pool
        if not fresh:
            return None
        path = chooser.choice(fresh)
        used.add(path)
        return Image.open(path)

    def paint_header(canvas, x, y, width):
        draw_mark(canvas, x, y, px(18))
        draw_text(canvas, fonts, x + px(24), y + px(9), "A-SOUL 日程", Style(12.5, bold=True, color=MUTED), anchor="lm")
        draw_text(canvas, fonts, x, y + px(30), title, Style(26, bold=True))
        draw_text(canvas, fonts, x, y + px(68), subtitle, Style(13, color=MUTED))

    card.add(px(86), paint_header, gap=0)

    for day in days:
        def paint_day(canvas, x, y, width, day=day):
            right = draw_text(canvas, fonts, x, y + px(11), f"{day.day.month}月{day.day.day}日", Style(16, bold=True), anchor="lm")
            right = draw_text(canvas, fonts, right + px(6), y + px(11), "周" + WEEKDAYS[day.day.weekday()],
                              Style(13, color=MUTED), anchor="lm")
            if day.today:
                draw_chip(canvas, fonts, right + px(8), y + px(1), "今天", PRIMARY, BRAND_SOFT)
            ImageDraw.Draw(canvas).line((x, y + px(27), x + width, y + px(27)), fill=LINE, width=max(1, px(0.5)))

        card.add(px(28), paint_day, gap=20)
        if not day.entries:
            card.add(px(18), lambda canvas, x, y, w: draw_text(canvas, fonts, x, y, "暂无直播",
                                                                Style(13.5, color=MUTED)), gap=10)
            continue
        for entry in day.entries:
            row(card, entry, sticker(entry.members), compact)

    footer(card, "日程", source)
    return card.render()


def row(card: Card, entry: Entry, art: Image.Image | None, compact: bool) -> None:
    fonts = card.fonts
    pad = px(10 if compact else 12)
    time_style = Style(18 if not compact else 16.5, bold=True, color=MUTED if entry.cancelled else INK)
    time_w = measure(fonts, "00:00", time_style) + px(14)
    art_size = px(44 if compact else 58)
    text_x = pad + time_w
    text_w = card.inner - text_x - pad - (art_size + px(10) if art is not None else 0)
    title_style = Style(14.5 if compact else 15, bold=True, color=MUTED if entry.cancelled else INK)
    lines = wrap(fonts, entry.title, title_style, text_w, max_lines=1 if compact else 2)
    step = px(22)
    content = px(20) + px(7) + len(lines) * step
    height = max(content, art_size if art is not None else 0) + 2 * pad

    def paint(canvas, x, y, width):
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((x, y, x + width, y + height), radius=px(8), fill=BRAND_SOFT if entry.highlight else PAGE)
        if entry.highlight:
            draw.rounded_rectangle((x, y + px(10), x + px(3), y + height - px(10)), radius=px(2), fill=BRAND)
        draw_text(canvas, fonts, x + pad + px(2), y + pad, f"{entry.start:%H:%M}", time_style)
        cx, cy = x + text_x, y + pad
        if entry.live_now:
            cx = draw_chip(canvas, fonts, cx, cy, "直播中", SUCCESS, SUCCESS_BG, dot=SUCCESS) + px(5)
        if entry.cancelled:
            cx = draw_chip(canvas, fonts, cx, cy, "已取消", ERROR, ERROR_BG) + px(5)
        if entry.highlight:
            cx = draw_chip(canvas, fonts, cx, cy, "特别关注", SURFACE, PRIMARY) + px(5)
        if entry.category:
            cx = draw_chip(canvas, fonts, cx, cy, entry.category, MUTED, SURFACE) + px(5)
        for name in entry.members:
            fg, bg = member_style(name)
            cx = draw_chip(canvas, fonts, cx, cy, name, fg, bg) + px(5)
        ty = cy + px(27)
        for text in lines:
            right = draw_text(canvas, fonts, x + text_x, ty, text, title_style)
            if entry.cancelled:
                draw.line((x + text_x, ty + step // 2, right, ty + step // 2), fill=MUTED, width=px(1))
            ty += step
        if art is not None:
            picture = ImageOps.contain(art.convert("RGBA"), (art_size, art_size), Image.Resampling.LANCZOS)
            canvas.alpha_composite(picture, (x + width - pad - art_size + (art_size - picture.width) // 2,
                                             y + (height - picture.height) // 2))

    card.add(height, paint, gap=8)
