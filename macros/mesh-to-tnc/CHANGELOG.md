# Changelog

All notable changes to the `mesh-to-tnc` macro are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.2.0] - 2026-07-23

### Added
- `_CNCConfigDialog` — full GUI with 5 tabs: Format, Tool, Feeds, Scan, Heights
- Format chooser dropdown: G-code (CAMotics/LinuxCNC/GRBL) or Heidenhain TNC
- Tool number, diameter, RPM settings in dialog
- Rapid / cutting / plunge feed settings in dialog
- Scan step X/Y with live RAM/file size estimate
- Safe height / clearance height settings in dialog
- File save dialog (defaults to Desktop)
- G-code output format with proper headers (`%`, `O`, `G21`, `G90`, `G17`, `G40`, `G43`, `G49`, `M30`)
- Tool info and scan params written as G-code comments in header

### Fixed
- `mesh.getVertices()` → `mesh.Points` (FreeCAD 1.0+ API)
- CAMotics compatibility via standard G-code output

## [1.0.0] - 2026-07-23

### Added
- Initial release: FreeCAD mesh to Heidenhain TNC converter
- Raster scan toolpath generation with zigzag pattern
- Heightmap-based Z interpolation from mesh vertices
- Configurable CNC parameters (tool, feeds, spindle speed)
- Configurable scan resolution (STEP_X, STEP_Y)
- Stream output to file (low memory usage)
- MemoryError handling for large meshes
