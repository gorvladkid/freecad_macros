# PNG-to-Mesh — FreeCAD CNC Plate Generator

A FreeCAD macro that converts a PNG/JPG image into a 3D solid mesh plate for CNC milling.

## What It Does

Generates a relief heightmap from an image where:
- **Dark pixels** → carved deeper into the plate
- **Light/white pixels** → remain at the surface
- Transparent pixels (alpha=0) → treated as white background

The output is a watertight OBJ mesh (with top surface, flat bottom, and side walls) imported into FreeCAD as a `Mesh::Feature` object.

## Installation

1. Copy `png-to-mesh.py` to your FreeCAD Macros directory:
   - **macOS**: `~/Library/Application Support/FreeCAD/Macro/`
   - **Windows**: `%APPDATA%\FreeCAD\Macro\`
   - **Linux**: `~/.local/share/FreeCAD/Macro/`
2. Restart FreeCAD or reload macros via **Macro → Macros → Refresh**

## Usage

1. Open FreeCAD with an active document
2. **Option A** — Select an image object in the document that has an `ImageFile` or `FileName` property, then run the macro
3. **Option B** — Run the macro directly; a file dialog will open to pick an image
4. The mesh will be imported as `CNC_Solid_Plate`

## Configuration

Edit these values at the top of `png_to_solid_plate()` (line ~33):

| Parameter | Default | Description |
|---|---|---|
| `max_carving_depth` | `9.0` mm | Maximum depth of carved recesses |
| `plate_thickness` | `10.0` mm | Total thickness of the blank plate |
| `pixel_size` | `0.25` mm | Physical XY size of one pixel |

**Example**: A 400×300 px image at `pixel_size=0.25` produces a `100×75 mm` plate.

## Supported Formats

PNG, JPG, JPEG (via Qt image loader)

## Requirements

- FreeCAD 0.19+ (uses PySide/Qt)
- Python 3
