# AGENTS.md — AI Agent Instructions

## Purpose
This file is the **source of truth** for AI agents working on this repository. Read it first in every new session.

## Repository
FreeCAD macros for CNC manufacturing. Python scripts running inside FreeCAD 1.0+ (PySide6/Qt6).

## Structure
```
freecad_macros/
  AGENTS.md                          ← you are here
  macros/
    png-to-mesh/
      AGENT.md                       ← read this for png-to-mesh context
      png-to-mesh-choose-color.py    ← main script
      README.md, CHANGELOG.md, IMPROVEMENTS.md
    mesh-to-tnc/
      AGENT.md                       ← read this for mesh-to-tnc context
      mesh-to-tnc.py                 ← main script
      README.md, CHANGELOG.md, IMPROVEMENTS.md
```

## How to Use This System

### Starting a new session
1. Read this `AGENTS.md` for repo overview
2. Read the relevant `macros/*/AGENT.md` for the macro you're working on
3. Read the Python source file for exact current state
4. Check `CHANGELOG.md` for recent changes
5. Check `IMPROVEMENTS.md` for known issues

### Making changes
1. Read the `AGENT.md` in the target macro folder first
2. Understand the architecture before editing
3. Follow existing code style (no comments unless asked, PySide6 compat)
4. Update `CHANGELOG.md` with your changes
5. Update `IMPROVEMENTS.md` if you fixed or introduced issues
6. Update `README.md` if user-facing behavior changed
7. Update `AGENT.md` if architecture changed

### FreeCAD/PySide6 rules
- Always use `mesh.Points` (not `mesh.getVertices()` — removed in 1.0+)
- Always use `dialog.exec()` (not `exec_()` — deprecated)
- Always use `event.position()` (not `event.pos()` — deprecated)
- Import PySide6 directly: `from PySide6 import QtWidgets` or `from PySide import QtWidgets` (FreeCAD shims both)
- `QImage.stackBlur()` does not exist — use `QGraphicsBlurEffect` via scene render

### Code conventions
- Module-level `DEFAULTS` dict or constants for configuration
- Single underscore prefix for internal functions/classes (`_write_gcode`, `_CNCConfigDialog`)
- Stream I/O for large outputs (no list accumulation)
- `try/finally` for temp file cleanup
- `if __name__ == "__main__":` guard at bottom
- Ukrainian UI strings in dialogs/console
- No comments in code unless explicitly requested

### File update checklist
When changing a script, update these files in the same folder:
- [ ] `AGENT.md` — if architecture or config changed
- [ ] `README.md` — if usage or parameters changed
- [ ] `CHANGELOG.md` — always, add entry under `[Unreleased]`
- [ ] `IMPROVEMENTS.md` — if you fixed or discovered issues

## Macro Summary

### png-to-mesh
Image → 3D heightmap mesh for CNC. Outputs watertight OBJ. Interactive color picker to choose which color maps to surface vs carved depth.

### mesh-to-tnc
Mesh → CNC program. G-code or Heidenhain TNC. Full config dialog with tool, feeds, scan resolution. Zigzag raster toolpath.
