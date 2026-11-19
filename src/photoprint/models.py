"""Plain data models: edits applied to a photo, and presets describing a print.

All physical sizes are in inches. Presets are stored as JSON (see presets/).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

Intent = Literal["perceptual", "relative", "saturation", "absolute"]
Placement = Literal["center", "gallery"]


@dataclass
class Crop:
    """Crop rectangle in normalised coordinates (0..1) of the rotated image."""

    x: float = 0.0
    y: float = 0.0
    w: float = 1.0
    h: float = 1.0


@dataclass
class Edits:
    """Non-destructive edits, saved as a sidecar next to the photo."""

    rotate: int = 0  # clockwise degrees: 0, 90, 180, 270
    crop: Crop | None = None  # None = auto centre-crop to the print ratio
    exposure: float = 0.0  # stops, -2..+2
    contrast: float = 0.0  # -1..+1
    temperature: float = 0.0  # -1 (cooler) .. +1 (warmer)
    tint: float = 0.0  # -1 (green) .. +1 (magenta)
    saturation: float = 0.0  # -1 (mono) .. +1
    sharpen: float = 0.5  # output sharpening amount, 0..1

    @classmethod
    def from_dict(cls, d: dict) -> "Edits":
        d = dict(d)
        crop = d.pop("crop", None)
        return cls(crop=Crop(**crop) if crop else None, **d)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def load(cls, path: Path) -> "Edits":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))


@dataclass
class Preset:
    """Everything needed to print: paper, image size, borders, colour and driver settings.

    The image size is given portrait (short side first). If the cropped photo is
    landscape, the whole layout is rotated to a landscape page automatically.
    """

    name: str
    paper_w: float  # inches, portrait
    paper_h: float
    image_w: float  # inches, portrait (short side)
    image_h: float
    placement: Placement = "center"
    gallery_bottom_ratio: float = 0.6  # gallery: share of vertical white space below the image
    min_margin: float = 0.125  # smallest margin allowed (printer's unprintable edge)
    ppi: int = 300
    icc_profile: str | None = None  # path to paper .icc; None = print sRGB (no conversion)
    intent: Intent = "relative"
    black_point_compensation: bool = True
    devmode: str | None = None  # path to saved driver settings (Windows)
    notes: str = ""

    def __post_init__(self) -> None:
        if self.image_w > self.image_h:
            self.image_w, self.image_h = self.image_h, self.image_w
        if self.paper_w > self.paper_h:
            self.paper_w, self.paper_h = self.paper_h, self.paper_w

    @property
    def aspect(self) -> float:
        """Portrait aspect ratio of the image box (w / h, <= 1)."""
        return self.image_w / self.image_h

    @classmethod
    def load(cls, path: Path) -> "Preset":
        path = Path(path)
        data = json.loads(path.read_text())
        preset = cls(**data)
        # Resolve relative file paths against the preset's folder.
        for attr in ("icc_profile", "devmode"):
            value = getattr(preset, attr)
            if value and not Path(value).is_absolute():
                setattr(preset, attr, str((path.parent / value).resolve()))
        return preset

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2))


@dataclass
class PageLayout:
    """Pixel geometry of a rendered page."""

    page_px: tuple[int, int]  # (width, height)
    image_box: tuple[int, int, int, int]  # (left, top, width, height)
    landscape: bool
    margins_in: dict[str, float] = field(default_factory=dict)
