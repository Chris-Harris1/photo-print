# photoprint — notes for Claude Code

A small Windows desktop app for printing photos on Chris's **Canon PIXMA PRO-100**:
crop to standard sizes, basic colour adjustments, white (gallery) borders, and
colour managed with his own paper ICC profiles. Full plan: `PLAN.md`.

## Ground rules
- **Colour is converted exactly once, by the app.** When a paper ICC profile is
  used, the Canon driver must be set to *No colour correction* (saved in the
  preset's DEVMODE). Never let the driver and the app both manage colour.
- **Print at 100% scale, physical inches.** Layout is computed in inches and
  rendered at the preset's ppi (300). The print module maps page pixels to
  device pixels and subtracts the printer's physical offset.
- **Engine stays UI- and Windows-free** (`src/photoprint/engine`). Anything that
  touches pywin32 lives in `src/photoprint/printing/windows.py` and is imported
  lazily so tests run anywhere.
- Keep v1 scope tight (see PLAN.md "Out of scope"): no RAW, no local edits, no
  multi-photo sheets yet.

## Layout
```
src/photoprint/
  models.py          Edits, Crop, Preset (JSON), PageLayout
  engine/load.py     open + EXIF orientation + convert to sRGB working space
  engine/crop.py     rotate, centre/aspect crop
  engine/adjust.py   exposure, WB, contrast, saturation (float32), output sharpening
  engine/layout.py   page geometry, centre/gallery borders, min-margin checks
  engine/color.py    LittleCMS (Pillow ImageCms): sRGB -> paper ICC, soft proof
  engine/render.py   full pipeline + fast preview
  engine/targets.py  geometry grid and colour test targets
  printing/windows.py  DEVMODE capture/restore + GDI printing (UNVERIFIED spike)
  cli.py             `photoprint` command
presets/             example presets (JSON). Local presets/ICC/devmode are git-ignored.
tests/               pytest, engine only
```

## Commands
```powershell
py -3.12 -m venv .venv; .venv\Scripts\activate
pip install -e ".[dev,windows,ui]"
pytest
photoprint printers
photoprint capture-devmode --printer "Canon PRO-100 series" --out presets/local/luster.devmode.json
photoprint target geometry --preset presets/example-8x10-letter-gallery.json --out out/grid.tif --print
```

## Status
- [x] Engine: crop, adjustments, layout, ICC conversion, preview, targets, tests
- [ ] **Milestone 1 — print spike (next).** `printing/windows.py` was written
      without Windows access; every `VERIFY` comment needs checking on the real
      machine. Done when the geometry target prints with every 1-inch square
      measuring 1 inch and borders within ±0.5 mm.
- [ ] Milestone 3 — PySide6 UI
- [ ] Milestone 4 — preset editor + one-click print
- [ ] Milestone 5 — soft proof toggle, gamut warning, PyInstaller .exe

## Known v1 limitations
- Working space is 8-bit sRGB; Adobe RGB files are clipped to sRGB on load.
- ICC transforms are 8-bit (Pillow ImageCms). Fine for prints; revisit if banding shows.
