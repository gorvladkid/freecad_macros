# png-to-mesh.py — Best Practices & SOC 2 Review

## Fixed (prior iterations)

- Face winding unified to CCW
- Temp file cleanup via `try/finally`
- Stream-write instead of list accumulation
- Image downscaling with `MAX_RESOLUTION`
- PySide6-compatible blur via `QGraphicsBlurEffect`
- `if __name__ == "__main__"` guard
- Specific exception handling (`FileNotFoundError`, `PermissionError`)

---

## Remaining Issues

### SOC 2 — Security & Integrity

#### 1. No input validation on config constants (Medium)

`PIXEL_SIZE`, `MAX_CARVING_DEPTH`, `PLATE_THICKNESS` accept any value including negative or zero. A negative `pixel_size` produces an inverted or degenerate mesh.

**Fix**: Validate at start of `png_to_solid_plate()`:
```python
for name, val in [("PIXEL_SIZE", PIXEL_SIZE), ...]:
    if not isinstance(val, (int, float)) or val <= 0:
        App.Console.PrintError(f"Невірне значення {name}={val}\n")
        return
```

#### 2. No path sanitization on selected object (Low)

`_resolve_image_path` trusts `selected_obj.ImageFile` / `selected_obj.FileName` directly. In a shared/malicious FreeCAD file this could read arbitrary filesystem paths.

**Fix**: Validate the path is within expected directories or at least check `os.path.isfile()` before proceeding (already partially done in `_load_image`).

#### 3. Hardcoded temp filename — race condition (Medium)

`fc_solid_plate.obj` is a fixed name in a shared temp directory. Two concurrent macro runs will overwrite each other.

**Fix**: Use `tempfile.NamedTemporaryFile` or append a UUID:
```python
temp_obj_path = os.path.join(tempfile.gettempdir(), f"fc_plate_{uuid4().hex[:8]}.obj")
```

#### 4. Temp file written to world-readable location (Low)

`tempfile.gettempdir()` is shared and world-readable. The OBJ file contains geometry data.

**Fix**: Use `tempfile.mkstemp()` which creates the file with restricted permissions (0600 on Unix).

#### 5. `except Exception` catch-all still present (Low)

Line 234 catches all exceptions generically. This can mask unexpected errors (e.g. `MemoryError`, `KeyboardInterrupt`).

**Fix**: Catch only expected exceptions or re-raise critical ones:
```python
except (FileNotFoundError, PermissionError, OSError) as e:
    ...
```

---

### Best Practices — Code Quality

#### 6. No type hints (Low)

All functions lack type annotations. Adding them improves IDE support and catches type bugs early.

**Fix**:
```python
def _load_image(image_path: str | None) -> QtGui.QImage | None:
def _resolve_image_path() -> str | None:
def _downscale_if_needed(img: QtGui.QImage) -> QtGui.QImage:
```

#### 7. No docstrings (Low)

No function has a docstring. Internal helpers should document purpose, parameters, and return value.

#### 8. Magic numbers in brightness formula (Low)

`0.299`, `0.587`, `0.114` are ITU-R BT.601 luminance coefficients. Should be named constants.

**Fix**:
```python
_LUMA_R = 0.299
_LUMA_G = 0.587
_LUMA_B = 0.114
```

#### 9. Module-level constants are mutable (Low)

Any code can overwrite `MAX_CARVING_DEPTH` at runtime. For a macro this is acceptable but not ideal.

**Fix**: Use a frozen dataclass or simply document that these are read-only config.

#### 10. No progress feedback for large images (Low)

For images >500px, the macro blocks FreeCAD with no visual feedback.

**Fix**: Periodic `App.Console.PrintMessage()` calls inside the vertex-writing loops, or a `QProgressDialog`.

---

## Priority Summary

| # | Issue | Category | Severity | Effort |
|---|-------|----------|----------|--------|
| 1 | No config validation | SOC 2 | Medium | Low |
| 3 | Hardcoded temp filename | SOC 2 | Medium | Low |
| 5 | Catch-all exception | SOC 2 | Low | Low |
| 2 | No path sanitization | SOC 2 | Low | Low |
| 4 | World-readable temp file | SOC 2 | Low | Low |
| 6 | No type hints | Best Practice | Low | Medium |
| 7 | No docstrings | Best Practice | Low | Medium |
| 8 | Magic numbers | Best Practice | Low | Low |
| 9 | Mutable constants | Best Practice | Low | Low |
| 10 | No progress feedback | Best Practice | Low | Medium |
