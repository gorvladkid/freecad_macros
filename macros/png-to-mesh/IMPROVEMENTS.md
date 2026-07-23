# png-to-mesh.py — Improvements & Best Practices Review

## Best Practices Audit

### What it does well
- Clear separation of config constants at the top of the function
- Handles both FreeCAD selection and file dialog fallback
- Transparent pixel handling (alpha=0 → white)
- Watertight mesh with side walls (solid-capable)
- Cleans up temp file after import
- Console feedback in Ukrainian for the user

### What needs improvement

---

### 1. Face Winding Order Inconsistency (High)

Different sides of the mesh use inconsistent vertex winding (CW vs CCW). This causes **inverted normals** on some faces, which breaks:
- STL/OBJ exports
- Boolean operations in FreeCAD
- CNC toolpath generators that rely on face normals

**Current (mixed):**
```python
# Left wall — CW
obj_lines.append(f"f {w0} {b0} {b1}\n")
obj_lines.append(f"f {w0} {b1} {w1}\n")

# Right wall — CCW
obj_lines.append(f"f {w0} {b1} {b0}\n")
obj_lines.append(f"f {w0} {w1} {b1}\n")
```

**Fix**: Unify all faces to CCW (counter-clockwise) winding when viewed from outside the mesh.

---

### 2. Temp File Not Cleaned on Failure (Medium)

If `Mesh.read()` throws, `os.remove(temp_obj_path)` is never reached.

```python
# Current — no finally block
temp_obj_path = os.path.join(temp_dir, "fc_solid_plate.obj")
with open(temp_obj_path, "w") as f:
    f.writelines(obj_lines)
loaded_mesh_data = Mesh.read(temp_obj_path)  # if this fails...
os.remove(temp_obj_path)  # ...this never runs
```

**Fix**: Use try/finally or move cleanup inside a `with` block context.

---

### 3. Memory: All OBJ Lines Held in List (Medium)

For a 1000×1000 image, `obj_lines` holds ~8M strings in memory simultaneously. This causes:
- High RAM usage (~2-4 GB)
- Slow GC pauses

**Fix**: Stream-write to the file directly instead of accumulating a list:
```python
with open(temp_obj_path, "w") as f:
    for y in range(height - 1, -1, -1):
        for x in range(width):
            # write vertices directly
```

---

### 4. No Image Downscaling / Resolution Limit (Medium)

A 4000×4000 image produces 32M vertices. No warning or limit exists.

**Fix**: Add a configurable `max_resolution` and downscale with `img.scaled()` if exceeded.

---

### 5. No Gaussian Blur / Smoothing Option (Low-Medium)

Raw pixel-to-height mapping produces visible raster steps on CNC surfaces. A blur pass would produce cleaner toolpaths.

**Fix**: Apply `QtGui.QImage` blur or use `PIL.ImageFilter.GaussianBlur` before processing.

---

### 6. Function Runs at Import Time (Low)

The last line `png_to_solid_plate()` executes immediately when the file is loaded. This is unexpected for macro files.

**Fix**: Wrap in a FreeCAD menu command:
```python
if __name__ == "__main__":
    png_to_solid_plate()
```

Or register as a toolbar button via `FreeCADGui.addCommand()`.

---

### 7. No Unit Awareness (Low)

All dimensions are hardcoded in mm. FreeCAD has its own unit system.

**Fix**: Query `FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Units")` or document that mm is assumed.

---

### 8. Error Handling is Generic (Low)

```python
except Exception as e:
    App.Console.PrintError(f"Помилка: {str(e)}\n")
```

Catches everything silently. Specific exceptions (file not found, invalid image, mesh read failure) should be handled separately with actionable messages.

---

### 9. No Progress Feedback for Large Images (Low)

For images >500px, the macro freezes FreeCAD with no progress indication.

**Fix**: Use `QtGui.QProgressDialog` or periodic `App.Console.PrintMessage()` calls.

---

### 10. Ukrainian Strings Not Externalized (Low)

All UI text is hardcoded in Ukrainian. No i18n/l10n support.

**Fix**: Move strings to a dict or use `FreeCAD.getUserMacroDir()` + config file for localization.

---

## Priority Summary

| # | Issue | Severity | Effort |
|---|-------|----------|--------|
| 1 | Face winding inconsistency | High | Low |
| 2 | Temp file not cleaned on error | Medium | Low |
| 3 | Memory: list accumulation | Medium | Medium |
| 4 | No resolution limit | Medium | Low |
| 5 | No blur/smoothing option | Low-Med | Medium |
| 6 | Runs at import time | Low | Low |
| 7 | No unit awareness | Low | Low |
| 8 | Generic error handling | Low | Low |
| 9 | No progress feedback | Low | Medium |
| 10 | No i18n support | Low | High |
