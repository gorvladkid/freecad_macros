# PNG-to-Mesh — FreeCAD CNC Plate Generator

A FreeCAD macro that converts a PNG/JPG image into a 3D solid mesh plate for CNC milling.

## What It Does

Generates a relief heightmap from an image where:
- **White pixels** → carved deeper into the plate
- **Black pixels** → remain at the surface
- Transparent pixels (alpha=0) → treated as white (carved deep)

The output is a watertight OBJ mesh (top surface, flat bottom, side walls) imported into FreeCAD as a `Mesh::Feature` object.

### Aspect-Ratio-Preserving Placement

When the image aspect ratio differs from the board size, the image is centered on the board and scaled to fit while preserving its proportions. The remaining area is flat board surface.

**Example**: 1024×1024 image on a 500×250 mm board:
- Image placed as 250×250 mm (centered on 500 mm width)
- Left/right borders (125 mm each) are flat board
- Top/bottom flush with board edges

## Installation

Copy `png-to-mesh-choose-color.py` to your FreeCAD Macros directory:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/FreeCAD/Macro/` |
| Windows | `%APPDATA%\FreeCAD\Macro\` |
| Linux | `~/.local/share/FreeCAD/Macro/` |

Restart FreeCAD or reload via **Macro > Macros > Refresh**.

## Usage

1. Open FreeCAD with an active document
2. **Option A** — Select an image object in the document (must have `ImageFile` or `FileName` property), then run the macro
3. **Option B** — Run the macro directly; a file dialog will open to pick an image
4. If `COLOR_MODE = "pick"` (default), a dialog opens with:
   - Image preview — click to select the surface color
   - Settings: depth, thickness, width, height
5. The mesh is imported as `CNC_Solid_Plate`

## Configuration

Edit the constants at the top of `png-to-mesh-choose-color.py`:

| Parameter | Default | Description |
|---|---|---|
| `MAX_CARVING_DEPTH` | `9.0` mm | Maximum depth of carved recesses (fallback if dialog cancelled) |
| `PLATE_THICKNESS` | `10.0` mm | Total thickness of the blank plate (fallback if dialog cancelled) |
| `OUTPUT_WIDTH` | `256.0` mm | Desired board width X (fallback if dialog cancelled) |
| `OUTPUT_HEIGHT` | `256.0` mm | Desired board height Y (fallback if dialog cancelled) |
| `MAX_RESOLUTION` | `2000` px | Auto-downscale if image exceeds this |
| `APPLY_BLUR` | `True` | Enable Gaussian blur pre-pass |
| `BLUR_RADIUS` | `1.5` | Blur strength (higher = smoother) |
| `COLOR_MODE` | `"pick"` | Color-to-depth mapping mode |

When `COLOR_MODE = "pick"`, the dialog overrides `MAX_CARVING_DEPTH`, `PLATE_THICKNESS`, `OUTPUT_WIDTH`, and `OUTPUT_HEIGHT` with user-entered values.

### Color Modes

| Mode | Behavior |
|---|---|
| `"auto"` | Analyzes image histogram. If mostly light → white=surface. If mostly dark → black=surface. |
| `"light-bg"` | White = surface, black = carved deep |
| `"dark-bg"` | Black = surface, white = carved deep |
| `"custom"` | Use `CUSTOM_MAP` for full control over brightness-to-depth mapping |
| `"pick"` | Interactive dialog — click on the image to choose the surface color, set all params |

### Custom Map

When `COLOR_MODE = "custom"`, define a list of `(brightness, depth_fraction)` pairs:

```python
CUSTOM_MAP = [
    (0.0, 1.0),   # black  → full depth
    (0.3, 0.0),   # dark gray → surface
    (0.7, 0.0),   # light gray → surface
    (1.0, 1.0),   # white  → full depth
]
```

- `brightness`: `0.0` = black, `1.0` = white
- `depth_fraction`: `0.0` = surface, `1.0` = max carving depth
- Values between stops are linearly interpolated

## Supported Formats

PNG, JPG, JPEG (via Qt image loader)

## Requirements

- FreeCAD 1.0+ (PySide6/Qt6)
- Python 3
