# Changelog

All notable changes to the `png-to-mesh` macro are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- `_calc_placement()` — aspect-ratio-preserving placement: image centered on board, scaled to fit
- `_ColorPickerDialog` — unified dialog with image preview, color picker, and all settings (depth, thickness, width, height)
- `COLOR_MODE = "pick"` — interactive dialog: click on image to select surface color
- `_pick_color_and_build_map()` — builds depth mapping from user-selected reference color
- `CUSTOM_MAP` — user-defined brightness-to-depth gradient stops with linear interpolation
- `_detect_color_mode()` — auto-detects background by analyzing mean brightness
- `_brightness_to_depth()` — unified brightness-to-depth mapping dispatcher
- `_interpolate_custom_map()` — linear interpolation over custom gradient stops
- `_compute_brightness()` — calculates mean brightness of non-transparent pixels

### Changed
- `_write_top_surface()` — generates full board grid; pixels outside image area are flat surface
- `_write_bottom_surface()` — uses board grid dimensions instead of image dimensions
- All face/index functions (`_idx_top`, `_idx_bot`, `_write_top_faces`, `_write_bottom_faces`, `_write_side_faces`) — use `cols`×`rows` board grid instead of image pixel dimensions
- Board grid: `cols = round(out_w / pixel_x) + 1`, `rows = round(out_h / pixel_y) + 1`
- Dialog parameters override module-level `OUTPUT_WIDTH`/`OUTPUT_HEIGHT`/`MAX_CARVING_DEPTH`/`PLATE_THICKNESS`
- `png-to-mesh-black-and-white.py` synced with choose-color version

### Fixed
- Reversed color mapping: white pixels now carve deep, black stays at surface
- `QImage.stackBlur()` AttributeError on PySide6 — replaced with `QGraphicsBlurEffect`
- Missing `QtCore` import in `_downscale_if_needed`
- PySide6 deprecation: `exec_()` → `exec()`
- PySide6 deprecation: `event.pos()` → `event.position()`

## [1.1.0] - 2026-07-23

### Changed
- Refactored monolithic function into single-responsibility helpers:
  - `_load_image`, `_resolve_image_path`, `_downscale_if_needed`, `_apply_blur`
  - `_write_obj_header`, `_write_top_surface`, `_write_bottom_surface`
  - `_write_top_faces`, `_write_bottom_faces`, `_write_side_faces`
  - `_idx_top`, `_idx_bot` index helpers
- Config constants moved from function scope to module level (`MAX_CARVING_DEPTH`, `PLATE_THICKNESS`, `PIXEL_SIZE`)
- OBJ written via stream I/O instead of in-memory list (reduces RAM from ~2-4 GB to near-zero for large images)
- Face winding unified to CCW on all surfaces (top, bottom, sides)
- Temp file cleanup moved to `try/finally` block
- Guarded execution with `if __name__ == "__main__"` to prevent auto-run on import
- Error handling: specific `FileNotFoundError` and `PermissionError` catches

### Added
- `MAX_RESOLUTION` — auto-downscale images exceeding 2000px
- `APPLY_BLUR` / `BLUR_RADIUS` — optional Gaussian blur pre-pass via `QGraphicsBlurEffect`
- `README.md` — installation, usage, configuration reference

### Fixed
- Inconsistent face winding (CW vs CCW) causing inverted normals on side walls
- Temp file not deleted when `Mesh.read()` fails
- `except Exception` catch-all replaced with specific exception types

## [1.0.0] - 2026-07-23

### Added
- Initial release: PNG-to-3D mesh converter for FreeCAD CNC milling
- Heightmap generation from image brightness (ITU-R BT.601 luminance)
- Watertight OBJ output with top surface, flat bottom, and side walls
- FreeCAD selection and file dialog fallback for image input
- Transparent pixel handling (alpha=0 treated as white)
- Configurable depth, thickness, and pixel scale
