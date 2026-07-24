# mesh-to-tnc.py — Best Practices & SOC 2 Review

## Current State

### What it does well
- Full GUI dialog with all parameters (no hardcoded config needed)
- Heightmap built once, reused for all scanlines (efficient)
- Output streamed line-by-line (no memory buffering)
- Zigzag scanning reduces rapid moves
- Specific error handling (PermissionError, MemoryError)
- Live RAM/file size estimate in scan tab
- Both G-code and Heidenhain TNC output formats
- Tool info and scan params in G-code comments for traceability

### Fixed (prior iterations)
- G-code output format with proper CAMotics-compatible headers
- `M30` program end with safety retract
- `mesh.getVertices()` → `mesh.Points` for FreeCAD 1.0+
- File save dialog instead of hardcoded output path

---

## Remaining Issues

### 1. No tool radius compensation (Medium)

Generated toolpaths follow the mesh surface exactly without offsetting for tool diameter. Inner features will be smaller, outer features larger than designed.

**Fix**: Offset scan path outward by `tool_diameter / 2`.

### 2. No feed rate optimization (Low)

All cutting moves use the same feed. Shallow areas could use faster feeds, steep areas slower.

**Fix**: Calculate local slope angle and adjust feed dynamically.

### 3. No arc interpolation (Low)

All moves are linear (`G01` / `L`). Smooth surfaces produce many short segments.

**Fix**: Detect collinear points and merge, or use arc commands (`G02`/`G03` / `CC`/`C`).

### 4. No progress save / resume (Low)

If generation is interrupted, the entire file must be regenerated.

**Fix**: Write incrementally and record completion state.

### 5. Heightmap uses max Z per cell (Low)

Multiple vertices in the same cell keep only the highest Z. Overlapping geometry detail may be lost.

**Fix**: Keep min/max/avg per cell, or use averaged Z.

### 6. No collision check (Low)

No verification that the tool holder clears the workpiece on steep areas.

**Fix**: Calculate holder clearance based on tool length and stepover angle.

### 7. No drilling cycle support (Low)

Only surface scanning is supported. Holes in the mesh are scanned line-by-line instead of using peck drilling cycles.

**Fix**: Detect cylindrical features and emit `CYCL DEF` (TNC) or `G81`-`G83` (G-code).

---

## Priority Summary

| # | Issue | Severity | Effort |
|---|-------|----------|--------|
| 1 | No tool radius compensation | Medium | Medium |
| 2 | No feed rate optimization | Low | Medium |
| 3 | No arc interpolation | Low | High |
| 4 | No progress save/resume | Low | High |
| 5 | Heightmap max-only per cell | Low | Low |
| 6 | No collision check | Low | High |
| 7 | No drilling cycle support | Low | High |
