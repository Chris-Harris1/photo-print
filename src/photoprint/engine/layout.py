"""Page geometry: where the image sits on the paper, in pixels."""

from __future__ import annotations

from ..models import PageLayout, Preset


class LayoutError(ValueError):
    pass


def compute_layout(preset: Preset, landscape: bool) -> PageLayout:
    """Place the image box on the page.

    centre:  equal margins left/right and top/bottom.
    gallery: equal left/right; vertical white space split so the bottom
             margin gets `gallery_bottom_ratio` of it (classic mat look).
    """
    pw, ph = preset.paper_w, preset.paper_h
    iw, ih = preset.image_w, preset.image_h
    if landscape:
        pw, ph, iw, ih = ph, pw, ih, iw

    spare_x, spare_y = pw - iw, ph - ih
    if spare_x < 0 or spare_y < 0:
        raise LayoutError(f"{iw}x{ih} in image does not fit on {pw}x{ph} in paper")

    left = spare_x / 2
    if preset.placement == "gallery":
        bottom = spare_y * preset.gallery_bottom_ratio
        top = spare_y - bottom
    else:
        top = bottom = spare_y / 2
    right = spare_x - left

    margins = {"top": top, "right": right, "bottom": bottom, "left": left}
    too_small = {k: v for k, v in margins.items() if v < preset.min_margin - 1e-9}
    if too_small:
        raise LayoutError(
            "margins below printer minimum "
            f"({preset.min_margin} in): " + ", ".join(f"{k}={v:.3f}" for k, v in too_small.items())
        )

    ppi = preset.ppi
    page_px = (round(pw * ppi), round(ph * ppi))
    box = (round(left * ppi), round(top * ppi), round(iw * ppi), round(ih * ppi))
    return PageLayout(page_px=page_px, image_box=box, landscape=landscape, margins_in=margins)
