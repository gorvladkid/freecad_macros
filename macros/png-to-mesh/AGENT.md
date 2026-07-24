# AGENT.md — png-to-mesh

## Purpose
FreeCAD macro that converts PNG/JPG images into 3D solid mesh plates for CNC milling. Generates a watertight OBJ heightmap imported as `Mesh::Feature`.

## Source Files
- `png-to-mesh-choose-color.py` — **main script** (~530 lines). Includes interactive color picker dialog with full parameter control.
- `png-to-mesh-black-and-white.py` — synced copy of the above.

## Architecture
```
png_to_solid_plate()             # entry point
  _resolve_image_path()          # selection or file dialog
  _load_image()                  # QImage from path
  _downscale_if_needed()         # cap at MAX_RESOLUTION
  _apply_blur()                  # QGraphicsBlurEffect (PySide6)
  _detect_color_mode()           # auto: mean brightness > 0.5?
  _pick_color_and_build_map()    # interactive: click image → depth mapping
    _ColorPickerDialog           # unified dialog: preview + all settings
  _calc_placement()              # aspect-ratio-preserving image placement on board
  _brightness_to_depth()         # dispatch: light-bg / dark-bg / custom / callable
  _write_top_surface()           # full board grid; image area = heightmap, border = flat
  _write_bottom_surface()        # flat bottom at Z=0 (board grid)
  _write_top_faces()             # CCW quads (board grid)
  _write_bottom_faces()          # CCW quads (board grid)
  _write_side_faces()            # 4 walls, CCW (board grid)
```

## Config (module-level constants)
| Constant | Default | Notes |
|---|---|---|
| `MAX_CARVING_DEPTH` | `9.0` mm | Max depth of recesses (fallback if dialog cancelled) |
| `PLATE_THICKNESS` | `10.0` mm | Total blank thickness (fallback if dialog cancelled) |
| `OUTPUT_WIDTH` | `256.0` mm | Board width X (fallback if dialog cancelled) |
| `OUTPUT_HEIGHT` | `256.0` mm | Board height Y (fallback if dialog cancelled) |
| `MAX_RESOLUTION` | `2000` px | Auto-downscale threshold |
| `APPLY_BLUR` | `True` | Enable blur pre-pass |
| `BLUR_RADIUS` | `1.5` | Blur strength |
| `COLOR_MODE` | `"pick"` | `"auto"` / `"light-bg"` / `"dark-bg"` / `"custom"` / `"pick"` |
| `CUSTOM_MAP` | `[(0,1),(0.3,0),(0.7,0),(1,1)]` | Brightness→depth stops for `"custom"` mode |

## Key Behaviors
- **Aspect-ratio preservation**: Image centered on board, scaled to fit. Border area is flat surface.
- **Board grid**: Vertices cover full board (`cols × rows`), not just image pixels. Image area mapped by `_calc_placement()` offsets.
- **Dialog override**: When `COLOR_MODE = "pick"`, dialog params override module constants.
- **Color modes**: `light-bg`=white→surface, `dark-bg`=black→surface, `pick`=interactive click, `custom`=gradient stops, `auto`=histogram mean
- **Winding**: All faces CCW when viewed from outside
- **Temp file**: Written to `tempfile`, cleaned in `finally` block
- **Stream I/O**: Writes directly to file, no list accumulation
- **PySide6 compat**: Uses `QGraphicsBlurEffect` (not `stackBlur`), `event.position()` (not `pos()`), `exec()` (not `exec_()`)

## FreeCAD API
- `FreeCAD`, `FreeCADGui`, `Mesh` modules
- PySide6: `QtGui.QImage`, `QtGui.QPixmap`, `QtWidgets.QGraphicsScene`, `QtWidgets.QGraphicsBlurEffect`
- `Mesh.read(path)` → imports OBJ

## Known Issues (see IMPROVEMENTS.md)
- No config validation (negative values)
- Hardcoded temp filename (race condition)
- `except Exception` catch-all present
- No type hints / docstrings
