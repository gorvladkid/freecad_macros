# AGENT.md — mesh-to-tnc

## Purpose
FreeCAD macro that converts a Mesh object into a CNC milling program. Outputs standard G-code (CAMotics/LinuxCNC/GRBL) or Heidenhain TNC format. All parameters configurable via GUI dialog.

## Source Files
- `mesh-to-tnc.py` — **main script** (403 lines). Includes config dialog class.

## Architecture
```
mesh_to_tnc()                  # entry point
  _get_selected_mesh()         # from FreeCAD selection
  _CNCConfigDialog(mesh)       # 5-tab GUI: Format, Tool, Feeds, Scan, Heights
  _build_heightmap()           # bin mesh.Points into grid, keep max Z per cell
  _interpolate_z()             # bilinear interpolation on heightmap
  _write_gcode()               # G-code output with headers
  _write_tnc()                 # Heidenhain TNC output
```

## Config (GUI dialog, stored in DEFAULTS dict)
| Key | Default | Dialog Tab | Notes |
|---|---|---|---|
| `program_name` | `"MESH_CNC"` | — | Internal, not editable in dialog |
| `tool_number` | `1` | Інструмент | Must match physical tool slot |
| `tool_diameter` | `3.0` mm | Інструмент | For G-code comments only |
| `spindle_speed` | `10000` RPM | Інструмент | |
| `rapid_feed` | `5000` mm/min | Подачі | Positioning moves |
| `cutting_feed` | `800` mm/min | Подачі | Cutting moves |
| `plunge_feed` | `300` mm/min | Подачі | Z plunge |
| `safe_height` | `5.0` mm | Висоти | Above workpiece for rapids |
| `clearance_height` | `2.0` mm | Висоти | Above surface before plunge |
| `scan_step_x` | `0.5` mm | Сканування | X resolution |
| `scan_step_y` | `0.5` mm | Сканування | Y resolution |
| `output_format` | `"gcode"` | Формат | `"gcode"` or `"tnc"` |
| `output_filename` | `"mesh_cnc"` | Формат | Extension auto-added |

## Key Behaviors
- **Zigzag scanning**: Alternates X direction per row to minimize rapids
- **Heightmap**: Built once from `mesh.Points`, reused for all scanlines
- **Bilinear interpolation**: Smooth Z between heightmap cells
- **Stream I/O**: Writes line-by-line, no memory buffering
- **Live estimate**: Scan tab shows point count, RAM, file size
- **File save**: Qt dialog defaults to `~/Desktop`

## Output Formats
### G-code
```
%
OMESH_CNC
( T1 D3.0mm S10000 )
G21 G90 G17 G40
G00 Z5.000
T1 M06
S10000 M03
G01 X... Z... F800
...
M05 G49 M30
%
```

### TNC
```
BEGIN PGM MESH_CNC MM
BLK FORM 0.1 Z ...
TOOL CALL 1 Z S10000
L Z+5.000 F5000 M3
L X... Z... F800
...
END PGM MESH_CNC MM
```

## FreeCAD API
- `FreeCAD`, `FreeCADGui`, `Mesh` modules
- `mesh.Points` — list of Vector (`.x`, `.y`, `.z`) — FreeCAD 1.0+ API
- `mesh.BoundBox` — `.XMin`, `.YMin`, `.ZMin`, `.XMax`, `.YMax`, `.ZMax`
- PySide6: `QtWidgets.QDialog`, `QTabWidget`, `QSpinBox`, `QDoubleSpinBox`, `QComboBox`, `QFileDialog`

## Known Issues (see IMPROVEMENTS.md)
- No tool radius compensation
- No feed rate optimization (slope-based)
- No arc interpolation (all linear moves)
- Heightmap uses max Z per cell only
- No drilling cycle support
