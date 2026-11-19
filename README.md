# photoprint

Crop, adjust and print photos on a Canon PIXMA PRO-100, with white borders and
ICC colour management using your own paper profiles. Windows only for printing;
the image engine runs anywhere.

## Quick start (Windows)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,windows,ui]"
pytest
```

1. Copy `presets/example-8x10-letter-gallery.json` into `presets/local/` and set
   `icc_profile` to your paper's `.icc` file.
2. Capture driver settings for that paper (choose media type, quality, and
   **No colour correction**):
   `photoprint capture-devmode --printer "Canon PRO-100 series" --out presets/local/luster.devmode.json`
   and set the preset's `devmode` to that file.
3. Check geometry on plain paper:
   `photoprint target geometry --preset presets/local/<preset>.json --print`
4. Print a photo:
   `photoprint print photo.jpg --preset presets/local/<preset>.json`

Edits can be supplied with `--edits edits.json` or a sidecar named
`photo.jpg.photoprint.json`:

```json
{"rotate": 0, "crop": null, "exposure": 0.3, "contrast": 0.2,
 "temperature": 0.1, "tint": 0, "saturation": 0.1, "sharpen": 0.5}
```

See `PLAN.md` for the roadmap and `CLAUDE.md` for working notes.
