"""The full pipeline: photo + edits + preset -> finished page in paper colour space."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from ..models import Edits, PageLayout, Preset
from .adjust import apply_adjustments, output_sharpen
from .color import to_paper
from .crop import apply_crop, centre_crop, orient_aspect, rotate
from .layout import compute_layout


@dataclass
class RenderResult:
    page: Image.Image  # 8-bit RGB, already in the paper profile's colour space
    layout: PageLayout
    effective_ppi: float  # photo pixels per printed inch before resampling


def prepare_image(photo: Image.Image, edits: Edits, preset: Preset) -> tuple[Image.Image, bool]:
    """Rotate and crop to the print aspect. Returns (cropped image, landscape?)."""
    img = rotate(photo, edits.rotate)
    w, h = img.size
    aspect = orient_aspect(preset.aspect, w, h)
    crop = edits.crop or centre_crop(w, h, aspect)
    return apply_crop(img, crop), aspect > 1


def render_page(photo: Image.Image, edits: Edits, preset: Preset) -> RenderResult:
    """Render a print-ready page. `photo` must already be sRGB (see engine.load)."""
    img, landscape = prepare_image(photo, edits, preset)
    layout = compute_layout(preset, landscape)
    left, top, bw, bh = layout.image_box

    effective_ppi = img.width / (bw / preset.ppi)

    img = apply_adjustments(img, edits)
    img = img.resize((bw, bh), Image.Resampling.LANCZOS)
    img = output_sharpen(img, edits.sharpen, preset.ppi)

    page = Image.new("RGB", layout.page_px, (255, 255, 255))
    page.paste(img, (left, top))

    # Paper white stays (255,255,255) under relative colorimetric; the whole page goes through the profile.
    page = to_paper(page, preset.icc_profile, preset.intent, preset.black_point_compensation)
    return RenderResult(page=page, layout=layout, effective_ppi=effective_ppi)


def render_preview(photo: Image.Image, edits: Edits, preset: Preset, max_px: int = 1600) -> Image.Image:
    """Fast sRGB preview of the whole page (no paper conversion) for the UI.

    Works on a downscaled copy so sliders stay responsive on 24 MP files.
    """
    small = photo.copy()
    small.thumbnail((max_px * 2, max_px * 2), Image.Resampling.BILINEAR)
    img, landscape = prepare_image(small, edits, preset)
    layout = compute_layout(preset, landscape)
    scale = max_px / max(layout.page_px)
    pw, ph = (round(v * scale) for v in layout.page_px)
    left, top, bw, bh = (round(v * scale) for v in layout.image_box)

    img = apply_adjustments(img, edits).resize((bw, bh), Image.Resampling.BILINEAR)
    page = Image.new("RGB", (pw, ph), (255, 255, 255))
    page.paste(img, (left, top))
    return page
