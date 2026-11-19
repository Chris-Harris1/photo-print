# Photo Print App — Build Plan

Living version: https://claude.ai/artifact/XANfyi7ipMqg911L7TPWPY

## Goal
A small Windows desktop app that takes a JPEG from crop to finished print on the
Canon PRO-100 in one window, with colour handled by your own paper ICC profiles.
Fewer clicks and less guessing than Qimage, for the prints you actually make.

**In scope (v1):** one photo per sheet; ratio-locked crop (4×6, 5×7, 8×10, 11×14,
13×19, square, free); exposure, contrast, white balance, saturation, print
sharpening; paper/print size with even or gallery borders; soft proof + ICC
conversion; per-paper presets with saved driver settings.

**Out of scope:** RAW, local edits, cataloguing, multiple photos per sheet, Mac.

## Workflow
Open → pick preset → crop → adjust → proof → print (one button, 100% scale,
saved driver settings).

## Architecture
UI (PySide6) → image engine (Pillow + NumPy, LittleCMS) → print module (pywin32,
saved DEVMODE, no colour correction) → PRO-100. Presets (JSON + DEVMODE), ICC
profiles and sidecar edits live on disk.

## Colour rule
Colour is converted once, by the app (relative colorimetric + BPC by default).
The driver is set to *No colour correction* whenever a paper profile is used.

## Milestones
1. **Print spike** — geometry target prints at exact size and position; colour not double-managed.
2. **Core engine** — CLI renders a preset to a TIFF matching the printed page. *(scaffolded)*
3. **Desktop UI** — smooth crop/adjust on a 24 MP D7200 file.
4. **Presets and printing** — three paper presets print correctly from a cold start.
5. **Soft proof and polish** — proof toggle, gamut warning, packaged .exe.

## Testing
Ruler/grid target for geometry (±0.5 mm); colour target compared against Qimage
trial or Print Studio Pro with the same profile; reference-render regression
tests; ~10–15 sheets total, mostly cheap paper.

## Open questions
- Which papers/ICC profiles first?
- Which print sizes are most common?
- Is the monitor calibrated?
