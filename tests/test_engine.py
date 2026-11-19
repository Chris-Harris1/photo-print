import numpy as np
import pytest
from PIL import Image, ImageCms

from photoprint.engine.adjust import apply_adjustments
from photoprint.engine.color import to_paper
from photoprint.engine.crop import centre_crop, rotate
from photoprint.engine.layout import LayoutError, compute_layout
from photoprint.engine.render import render_page, render_preview
from photoprint.models import Edits, Preset


def preset(**kw):
    base = dict(name="t", paper_w=8.5, paper_h=11, image_w=8, image_h=10)
    base.update(kw)
    return Preset(**base)


def gradient(w=600, h=400):
    x = np.linspace(0, 255, w, dtype=np.uint8)
    a = np.stack([np.tile(x, (h, 1))] * 3, axis=-1)
    a[..., 2] = 128
    return Image.fromarray(a, "RGB")


def test_centre_layout_margins():
    lay = compute_layout(preset(), landscape=False)
    assert lay.page_px == (2550, 3300)
    assert lay.image_box == (75, 150, 2400, 3000)
    assert lay.margins_in["top"] == pytest.approx(0.5)


def test_gallery_layout_puts_more_white_below():
    lay = compute_layout(preset(placement="gallery", gallery_bottom_ratio=0.6), landscape=False)
    m = lay.margins_in
    assert m["bottom"] == pytest.approx(0.6)
    assert m["top"] == pytest.approx(0.4)


def test_landscape_swaps_page():
    lay = compute_layout(preset(image_w=5, image_h=7), landscape=True)
    assert lay.page_px == (3300, 2550)
    assert lay.image_box[2:] == (2100, 1500)


def test_margin_below_printer_minimum_is_refused():
    with pytest.raises(LayoutError):
        compute_layout(preset(image_w=8.4, image_h=10), landscape=False)


def test_image_bigger_than_paper_is_refused():
    with pytest.raises(LayoutError):
        compute_layout(preset(image_w=13, image_h=19), landscape=False)


def test_centre_crop_matches_aspect():
    c = centre_crop(6000, 4000, 10 / 8)
    assert (c.w * 6000) / (c.h * 4000) == pytest.approx(10 / 8)
    assert c.x == pytest.approx((1 - c.w) / 2)


def test_rotate_90_swaps_size():
    assert rotate(gradient(), 90).size == (400, 600)


def test_no_edits_is_identity():
    img = gradient()
    assert apply_adjustments(img, Edits()) is img


def test_exposure_brightens():
    img = gradient()
    out = np.asarray(apply_adjustments(img, Edits(exposure=1.0)), dtype=float)
    assert out.mean() > np.asarray(img, dtype=float).mean()


def test_desaturate_gives_neutral():
    out = np.asarray(apply_adjustments(gradient(), Edits(saturation=-1.0)), dtype=int)
    assert np.abs(out[..., 0] - out[..., 2]).max() <= 1


def test_srgb_as_paper_profile_is_near_identity(tmp_path):
    icc = tmp_path / "srgb.icc"
    icc.write_bytes(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    img = gradient()
    out = to_paper(img, icc)
    diff = np.abs(np.asarray(out, dtype=int) - np.asarray(img, dtype=int))
    assert diff.max() <= 2


def test_render_landscape_photo_on_portrait_preset():
    result = render_page(gradient(6000 // 4, 4000 // 4), Edits(), preset())
    assert result.layout.landscape
    assert result.page.size == (3300, 2550)
    # Margins stay paper white
    assert result.page.getpixel((10, 10)) == (255, 255, 255)


def test_preview_is_small():
    prev = render_preview(gradient(3000, 2000), Edits(), preset(), max_px=800)
    assert max(prev.size) == 800
