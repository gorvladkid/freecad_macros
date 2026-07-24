# Mesh-to-TNC — FreeCAD Mesh to CNC Converter

A FreeCAD macro that converts a mesh object into a CNC milling program (G-code or Heidenhain TNC).

## What It Does

Scans the mesh surface in a zigzag raster pattern and generates a CNC program with:
- Linear moves following the mesh surface Z-heights
- Configurable tool, feeds, scan resolution via GUI dialog
- Output in **G-code** (CAMotics, LinuxCNC, GRBL) or **Heidenhain TNC** format

## Installation

Copy `mesh-to-tnc.py` to your FreeCAD Macros directory:

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/FreeCAD/Macro/` |
| Windows | `%APPDATA%\FreeCAD\Macro\` |
| Linux | `~/.local/share/FreeCAD/Macro/` |

Restart FreeCAD or reload via **Macro > Macros > Refresh**.

## Usage

1. Open FreeCAD with a document containing a Mesh object
2. Select the mesh in the model tree or 3D view
3. Run the macro
4. A **config dialog** opens with 5 tabs — set your parameters
5. Click **"Згенерувати"** — a file save dialog appears (defaults to Desktop)
6. Open the generated file in CAMotics or load on your CNC controller

## Config Dialog

### Tab: Формат (Format)
| Setting | Description |
|---|---|
| Формат | `G-code (CAMotics / LinuxCNC / GRBL)` or `Heidenhain TNC` |
| Ім'я файлу | Output filename (extension added automatically) |

### Tab: Інструмент (Tool)
| Setting | Default | Description |
|---|---|---|
| Номер інструменту | `1` | Tool slot number (`T1`, `T2`, ...) — must match physical tool in magazine |
| Діаметр фрези | `3.0` mm | Cutter diameter — used in G-code comments for reference |
| Оберти (RPM) | `10000` | Spindle speed |

### Tab: Подачі (Feeds)
| Setting | Default | Description |
|---|---|---|
| Подача позиц. | `5000` mm/min | Rapid positioning feed |
| Подача різання | `800` mm/min | Cutting feed |
| Подача занурення | `300` mm/min | Plunge feed |

### Tab: Сканування (Scan)
| Setting | Default | Description |
|---|---|---|
| Крок по X | `0.5` mm | Distance between X scan points |
| Крок по Y | `0.5` mm | Distance between Y scan lines |

Smaller values = finer detail, larger file, more RAM. A live estimate shows point count, RAM usage, and file size.

### Tab: Висоти (Heights)
| Setting | Default | Description |
|---|---|---|
| Безпечна висота | `5.0` mm | Height above workpiece for rapid moves |
| Висота перед plunge | `2.0` mm | Clearance above surface before each plunge |

## Memory Efficiency

- Heightmap built once from mesh vertices (fixed memory)
- Output streamed line-by-line (no buffering)
- Each scanline processed independently

For large meshes, increase scan step values in the dialog.

## Supported Formats

- **Input**: FreeCAD Mesh objects (`Mesh::Feature`)
- **Output**: G-code (`.gcode`) or Heidenhain TNC (`.tnc`)

## Requirements

- FreeCAD 1.0+ (PySide6)
- Python 3
