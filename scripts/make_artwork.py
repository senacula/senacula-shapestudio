"""Rasterise the Senacula Shape Studio mark at every size the packaging needs, from the brand
kit's SVG files (ADR-070): the Windows .ico, the MSIX tile set, the Store display logos, the
posters, hero images and box art, the website icons and the PNG icon set the app serves.

The drawing simplifies as it shrinks instead of being scaled (brand/README.md): ``shape-tile.svg``
at 96 px and up, ``shape-tile-48.svg`` for 40 to 95 px, ``shape-tile-24.svg`` for 21 to 39 px and
``shape-tile-16.svg`` at 20 px and under. This script never scales the large drawing below
96 px; it picks the file for the size and renders it with headless Chromium (Playwright, a
development dependency), so the pixels are the brand kit's own, not a redrawing.

    .venv/Scripts/python scripts/make_artwork.py [--kit <brand folder>]
"""
# Copyright 2026 Ratul Roy (royal-programmer) and the Hivemind contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import io
import re
import shutil
import struct
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
DEFAULT_KIT = Path(r"C:\Users\ratul.roy\Desktop\Temp\Hivemind\app\brand")
KEY = "shape"
CORAL = "#D5582F"
LIGHT = "#F4F4F5"
COPIED = (
    "tile",
    "tile-48",
    "tile-24",
    "tile-16",
    "chrome",
    "mark",
    "mono",
    "mono-light",
    "spinner",
)
ICON_PNG_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 180, 192, 256, 512)


def level_file(size: int) -> str:
    """The brand kit's file for a rendered size, per brand/README.md."""
    if size >= 96:
        return f"{KEY}-tile.svg"
    if size >= 40:
        return f"{KEY}-tile-48.svg"
    if size >= 21:
        return f"{KEY}-tile-24.svg"
    return f"{KEY}-tile-16.svg"


def without_background(svg: str) -> str:
    """The tile drawing on transparent: drop the rounded square. Hollow seats keep their fill
    (the tile colour), which is what Windows paints behind a transparent tile anyway."""
    return re.sub(
        r'<rect x="0" y="0" width="64" height="64" rx="14" fill="#[0-9A-Fa-f]{6}"/>',
        "",
        svg,
        count=1,
    )


def recolour(svg: str, old: str, new: str) -> str:
    return re.sub(re.escape(old), new, svg, flags=re.IGNORECASE)


class Renderer:
    """Headless Chromium draws an SVG document at an exact pixel size on transparent."""

    def __init__(self) -> None:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._page = self._browser.new_page(
            viewport={"width": 64, "height": 64}, device_scale_factor=1
        )

    def close(self) -> None:
        self._browser.close()
        self._pw.stop()

    def render(self, svg: str, width: int, height: int | None = None) -> Image.Image:
        height = height or width
        svg = re.sub(
            r'\swidth="\d+"\sheight="\d+"', f' width="{width}" height="{height}"', svg, count=1
        )
        html = (
            "<!doctype html><html><head><style>html,body{margin:0;background:transparent}"
            f"svg{{display:block;width:{width}px;height:{height}px}}</style></head><body>{svg}</body></html>"
        )
        self._page.set_viewport_size({"width": width, "height": height})
        self._page.set_content(html)
        png = self._page.screenshot(
            omit_background=True, clip={"x": 0, "y": 0, "width": width, "height": height}
        )
        return Image.open(io.BytesIO(png)).convert("RGBA")


def write_ico(path: Path, images: list[Image.Image]) -> None:
    """An .ico whose entries are PNG-compressed and each drawn at its own level (Pillow's
    ICO writer would scale one drawing to every size)."""
    entries = []
    blobs = []
    for im in images:
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        blobs.append(buf.getvalue())
        w, h = im.size
        entries.append((0 if w >= 256 else w, 0 if h >= 256 else h))
    offset = 6 + 16 * len(images)
    out = bytearray(struct.pack("<HHH", 0, 1, len(images)))
    for (w, h), blob in zip(entries, blobs, strict=True):
        out += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    for blob in blobs:
        out += blob
    path.write_bytes(bytes(out))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", default=str(DEFAULT_KIT))
    args = ap.parse_args()
    kit = Path(args.kit)
    svgs = {name: (kit / f"{KEY}-{name}.svg").read_text(encoding="utf-8") for name in COPIED}

    pk = ROOT / "packaging"
    assets = pk / "msix" / "Assets"
    assets.mkdir(parents=True, exist_ok=True)
    store = pk / "store-assets"
    store.mkdir(exist_ok=True)
    site_assets = ROOT / "site" / "assets"
    brand_static = ROOT / "src" / "shapestudio" / "static" / "brand"
    for folder in (site_assets, brand_static):
        folder.mkdir(parents=True, exist_ok=True)
        for name in COPIED:  # the kit is the source of truth; copies are verbatim
            shutil.copy2(kit / f"{KEY}-{name}.svg", folder / f"{KEY}-{name}.svg")
    shutil.copy2(kit / f"{KEY}-tile.svg", site_assets / "icon.svg")

    r = Renderer()
    try:

        def tile_png(size: int) -> Image.Image:
            return r.render(svgs[level_file(size)[len(KEY) + 1 : -4]], size)

        def plate_png(w: int, h: int, pad: float = 0.18) -> Image.Image:
            """Transparent tile with the drawing centred (Windows paints the colour behind)."""
            side = int(min(w, h) * (1 - 2 * pad))
            lvl = level_file(side)[len(KEY) + 1 : -4]
            drawing = r.render(without_background(svgs[lvl]), side)
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            img.alpha_composite(drawing, ((w - side) // 2, (h - side) // 2))
            return img

        # the PNG icon set the app serves at /icon-<n>.png and the site's touch icon
        for size in ICON_PNG_SIZES:
            tile_png(size).save(brand_static / f"icon-{size}.png", optimize=True)
        shutil.copy2(brand_static / "icon-512.png", site_assets / "icon-512.png")
        shutil.copy2(brand_static / "icon-180.png", site_assets / "icon-180.png")
        shutil.copy2(brand_static / "icon-16.png", site_assets / "icon-16.png")
        shutil.copy2(brand_static / "icon-32.png", site_assets / "icon-32.png")

        # the installer / exe icon: one entry per size, each at its own level
        write_ico(pk / "ShapeStudio.ico", [tile_png(s) for s in (16, 24, 32, 48, 64, 128, 256)])

        # Store display logos
        for size in (71, 150, 300):
            tile_png(size).save(store / f"display-1x1-{size}.png", optimize=True)

        # MSIX tiles: transparent plates with the drawing at the right level
        scales = {
            "": 1.0,
            ".scale-125": 1.25,
            ".scale-150": 1.5,
            ".scale-200": 2.0,
            ".scale-400": 4.0,
        }
        for name, (w, h) in {
            "Square150x150Logo": (150, 150),
            "Square44x44Logo": (44, 44),
            "Wide310x150Logo": (310, 150),
            "StoreLogo": (50, 50),
        }.items():
            for suffix, f in scales.items():
                plate_png(round(w * f), round(h * f)).save(
                    assets / f"{name}{suffix}.png", optimize=True
                )
        plate_png(71, 71).save(assets / "Square71x71Logo.png", optimize=True)
        plate_png(310, 310).save(assets / "Square310x310Logo.png", optimize=True)
        plate_png(620, 300).save(assets / "SplashScreen.png", optimize=True)
        tile_png(44).save(
            assets / "Square44x44Logo.targetsize-44_altform-unplated.png", optimize=True
        )

        # posters, hero images and box art on the dark template, the colour mark over the glow
        from shapestudio.brand import write_store_artwork

        for p in write_store_artwork(ROOT, lambda size: r.render(svgs["mark"], size)):
            print(p.relative_to(ROOT))
    finally:
        r.close()
    print("artwork written")


if __name__ == "__main__":
    main()
