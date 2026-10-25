"""The Senacula Shape Studio poster template (dark ground, glow, lockup, tagline), the
family's layout (ADR-066), shared with Image Studio. The mark itself is no longer drawn here:
since ADR-070 it is the brand kit's SVG (a thin ring, six hollow seats, the presiding dais,
and Shape Studio's cube on the floor), rendered at the right level per size by
scripts/make_artwork.py; this module only composes the rendered mark into the artwork."""

# Copyright 2026 Ratul Roy (royal-programmer) and the Hivemind contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

FAMILY = "Senacula"
PRODUCT = "Shape Studio"
FULL_NAME = f"{FAMILY} {PRODUCT}"
VIOLET = "#5B4FD1"  # Senacula
CORAL = "#D5582F"  # Shape Studio
LIGHT = "#F4F4F5"
GROUND = "#09090b"
TAGLINE = ("Your own 3D studio.", "Free, local, honest.")

MarkRenderer = Callable[[int], object]  # size in px -> RGBA Pillow image of the colour mark


def _font(size: int, bold: bool):
    from PIL import ImageFont

    candidates = (
        ["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    )
    for name in candidates:
        for folder in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts"), Path("/Library/Fonts")):
            p = folder / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _glow(img, centre: tuple[int, int], radius: int, colour: str, peak: float = 0.38) -> None:
    """A soft radial glow of ``colour`` behind the mark: the only gradient allowed."""
    from PIL import Image, ImageDraw, ImageFilter

    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = centre
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=int(255 * peak))
    mask = mask.filter(ImageFilter.GaussianBlur(radius * 0.55))
    layer = Image.new("RGBA", (w, h), colour)
    img.paste(layer, (0, 0), mask)


def _fit_font(draw, text: str, size: int, bold: bool, max_width: float):
    """The largest font at or below ``size`` whose rendering of ``text`` fits ``max_width``."""
    while size > 8:
        f = _font(size, bold)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size = int(size * 0.94)
    return _font(size, bold)


def poster(
    width: int,
    height: int,
    render_mark: MarkRenderer,
    colour: str = CORAL,
    family: str = FAMILY,
    product: str = PRODUCT,
    tagline: tuple[str, str] = TAGLINE,
):
    """Store artwork on the dark ground (ADR-066): the mark in colour over a soft glow,
    "Senacula" in medium weight at about 55% of the product size, the product name large and
    regular, then a two-line tagline with the accent colour on the second line. Nothing sits
    within 8% of an edge. Tall (9:16), wide (16:9) and square (1:1) layouts."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (width, height), GROUND)
    d = ImageDraw.Draw(img)
    margin = 0.08
    if height > width:  # 9:16 poster
        mark_size = int(width * 0.42)
        mark_c = (width // 2, int(height / 3))
        text_w = width * (1 - 2 * margin)
        product_px = int(width * 0.105)
        tag_px = int(width * 0.046)
        text_top = mark_c[1] + mark_size // 2 + int(height * 0.06)
        centre_x = width // 2
    elif width > height:  # 16:9 hero
        mark_size = int(height * 0.5)
        mark_c = (int(width * 0.3), height // 2)
        text_w = width * 0.44
        product_px = int(height * 0.115)
        tag_px = int(height * 0.052)
        text_top = None  # vertically centred block on the right
        centre_x = None
    else:  # 1:1 box art
        mark_size = int(width * 0.36)
        mark_c = (width // 2, int(height * 0.36))
        text_w = width * (1 - 2 * margin)
        product_px = int(width * 0.095)
        tag_px = int(width * 0.042)
        text_top = mark_c[1] + mark_size // 2 + int(height * 0.05)
        centre_x = width // 2
    _glow(img, mark_c, int(mark_size * 0.9), colour)
    mark = render_mark(mark_size)
    img.alpha_composite(mark, (mark_c[0] - mark_size // 2, mark_c[1] - mark_size // 2))

    f_prod = _fit_font(d, product, product_px, False, text_w)
    f_fam = _fit_font(d, family, int(f_prod.size * 0.55), True, text_w)
    f_tag = _fit_font(d, max(tagline, key=len), tag_px, False, text_w)
    gap = int(f_prod.size * 0.18)
    lines = [
        (family, f_fam, LIGHT),
        (product, f_prod, LIGHT),
        (None, None, int(f_prod.size * 0.45)),  # spacer
        (tagline[0], f_tag, LIGHT),
        (tagline[1], f_tag, colour),
    ]
    heights = [(ln[2] if ln[0] is None else ln[1].size) for ln in lines]
    block_h = sum(heights) + gap * (len(lines) - 1)
    if text_top is None:
        text_top = (height - block_h) // 2
        left = int(width * 0.52)
    else:
        left = None
    y = text_top
    for (text, font, fill), hgt in zip(lines, heights, strict=True):
        if text is not None:
            tw = d.textlength(text, font=font)
            x = left if left is not None else int(centre_x - tw / 2)
            d.text((x, y), text, font=font, fill=fill)
        y += hgt + gap
    return img


STORE_ARTWORK = {
    "box-art-1x1-1080.png": (1080, 1080),
    "box-art-1x1-2160.png": (2160, 2160),
    "poster-9x16-720x1080.png": (720, 1080),
    "poster-9x16-1440x2160.png": (1440, 2160),
    "hero-16x9-1920x1080.png": (1920, 1080),
    "hero-16x9-3840x2160.png": (3840, 2160),
}


def write_store_artwork(root: Path, render_mark: MarkRenderer) -> list[Path]:
    """The Store posters, hero images and box art under packaging/store-assets.
    ``render_mark(size)`` returns the colour mark on transparent at ``size`` px (the kit's
    shape-mark.svg rendered by scripts/make_artwork.py, which also makes the icons and tiles)."""
    store = root / "packaging" / "store-assets"
    store.mkdir(parents=True, exist_ok=True)
    written = []
    for name, (w, h) in STORE_ARTWORK.items():
        p = store / name
        poster(w, h, render_mark).save(p, "PNG", optimize=True)
        written.append(p)
    return written


if __name__ == "__main__":
    raise SystemExit(
        "run scripts/make_artwork.py: it renders the brand kit's SVGs and writes everything"
    )
