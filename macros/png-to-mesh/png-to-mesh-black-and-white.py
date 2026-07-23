import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui
import tempfile
import os
import Mesh

# =========================================================
# CONFIGURATION (edit values in mm)
# =========================================================
MAX_CARVING_DEPTH = 9.0
PLATE_THICKNESS = 10.0
PIXEL_SIZE = 0.25
MAX_RESOLUTION = 2000
APPLY_BLUR = True
BLUR_RADIUS = 1.5
# =========================================================


def _load_image(image_path):
    if not image_path or not os.path.exists(image_path):
        return None
    img = QtGui.QImage(image_path)
    if img.isNull():
        App.Console.PrintError(f"Не вдалося завантажити зображення: {image_path}\n")
        return None
    return img


def _resolve_image_path():
    selection = Gui.Selection.getSelection()
    if selection:
        obj = selection[0]
        if hasattr(obj, "ImageFile"):
            return obj.ImageFile
        if hasattr(obj, "FileName"):
            return obj.FileName

    result = QtGui.QFileDialog.getOpenFileName(
        None, "Оберіть зображення", "", "Images (*.png *.jpg *.jpeg)"
    )
    path = result[0] if isinstance(result, tuple) else result
    return path if path else None


def _downscale_if_needed(img):
    from PySide import QtCore

    w, h = img.width(), img.height()
    if max(w, h) <= MAX_RESOLUTION:
        return img
    scale = MAX_RESOLUTION / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    App.Console.PrintMessage(
        f"Зображення {w}x{h} > {MAX_RESOLUTION}px. "
        f"Масштабування до {new_w}x{new_h}.\n"
    )
    return img.scaled(new_w, new_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)


def _apply_blur(img, radius):
    if not APPLY_BLUR or radius <= 0:
        return img

    qt_radius = min(int(radius * 20), 250)
    if qt_radius <= 0:
        return img

    try:
        from PySide6 import QtWidgets

        pixmap = QtGui.QPixmap.fromImage(img)
        scene = QtWidgets.QGraphicsScene()
        item = scene.addPixmap(pixmap)

        effect = QtWidgets.QGraphicsBlurEffect()
        effect.setBlurRadius(qt_radius)
        item.setGraphicsEffect(effect)

        result = QtGui.QImage(img.size(), img.format())
        result.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(result)
        scene.render(painter)
        painter.end()

        App.Console.PrintMessage(f"Застосовано blur (radius={radius}).\n")
        return result
    except Exception:
        App.Console.PrintMessage("Blur недоступний, пропускаємо.\n")
        return img


def _write_obj_header(f):
    f.write("# FreeCAD CNC Plate — auto-generated OBJ\n")


def _write_top_surface(f, img, width, height):
    for y in range(height - 1, -1, -1):
        for x in range(width):
            color = QtGui.QColor(img.pixel(x, y))
            if color.alpha() == 0:
                brightness = 1.0
            else:
                brightness = (
                    color.red() * 0.299
                    + color.green() * 0.587
                    + color.blue() * 0.114
                ) / 255.0

            depth = brightness * MAX_CARVING_DEPTH
            posZ = PLATE_THICKNESS - depth
            posX = x * PIXEL_SIZE
            posY = (height - 1 - y) * PIXEL_SIZE
            f.write(f"v {posX:.4f} {posY:.4f} {posZ:.4f}\n")


def _write_bottom_surface(f, width, height):
    for y in range(height - 1, -1, -1):
        for x in range(width):
            posX = x * PIXEL_SIZE
            posY = (height - 1 - y) * PIXEL_SIZE
            f.write(f"v {posX:.4f} {posY:.4f} 0.0000\n")


def _idx_top(y, x, width):
    return y * width + x + 1


def _idx_bot(y, x, width, total):
    return y * width + x + 1 + total


def _write_top_faces(f, width, height):
    for y in range(height - 1):
        for x in range(width - 1):
            i0 = _idx_top(y, x, width)
            i1 = _idx_top(y, x + 1, width)
            i2 = _idx_top(y + 1, x, width)
            i3 = _idx_top(y + 1, x + 1, width)
            # CCW winding when viewed from outside (top)
            f.write(f"f {i0} {i1} {i3}\n")
            f.write(f"f {i0} {i3} {i2}\n")


def _write_bottom_faces(f, width, height, total):
    for y in range(height - 1):
        for x in range(width - 1):
            i0 = _idx_bot(y, x, width, total)
            i1 = _idx_bot(y, x + 1, width, total)
            i2 = _idx_bot(y + 1, x, width, total)
            i3 = _idx_bot(y + 1, x + 1, width, total)
            # CCW winding when viewed from outside (bottom = looking up)
            f.write(f"f {i0} {i3} {i1}\n")
            f.write(f"f {i0} {i2} {i3}\n")


def _write_side_faces(f, width, height, total):
    for y in range(height - 1):
        # Left wall (x = 0)
        wt = _idx_top(y, 0, width)
        wb = _idx_top(y + 1, 0, width)
        bt = _idx_bot(y, 0, width, total)
        bb = _idx_bot(y + 1, 0, width, total)
        f.write(f"f {wt} {bt} {bb}\n")
        f.write(f"f {wt} {bb} {wb}\n")

        # Right wall (x = width - 1)
        wt = _idx_top(y, width - 1, width)
        wb = _idx_top(y + 1, width - 1, width)
        bt = _idx_bot(y, width - 1, width, total)
        bb = _idx_bot(y + 1, width - 1, width, total)
        f.write(f"f {wt} {bb} {bt}\n")
        f.write(f"f {wt} {wb} {bb}\n")

    for x in range(width - 1):
        # Front wall (y = 0)
        wt = _idx_top(0, x, width)
        wb = _idx_top(0, x + 1, width)
        bt = _idx_bot(0, x, width, total)
        bb = _idx_bot(0, x + 1, width, total)
        f.write(f"f {wt} {bb} {bt}\n")
        f.write(f"f {wt} {wb} {bb}\n")

        # Back wall (y = height - 1)
        wt = _idx_top(height - 1, x, width)
        wb = _idx_top(height - 1, x + 1, width)
        bt = _idx_bot(height - 1, x, width, total)
        bb = _idx_bot(height - 1, x + 1, width, total)
        f.write(f"f {wt} {bt} {bb}\n")
        f.write(f"f {wt} {bb} {wb}\n")


def png_to_solid_plate():
    image_path = _resolve_image_path()
    img = _load_image(image_path)
    if img is None:
        return

    img = _downscale_if_needed(img)
    img = _apply_blur(img, BLUR_RADIUS)

    width = img.width()
    height = img.height()
    total = width * height

    App.Console.PrintMessage(f"Розмір: {width}x{height} ({width * PIXEL_SIZE:.1f}x{height * PIXEL_SIZE:.1f} mm)\n")

    temp_obj_path = os.path.join(tempfile.gettempdir(), "fc_solid_plate.obj")
    try:
        with open(temp_obj_path, "w") as f:
            _write_obj_header(f)
            _write_top_surface(f, img, width, height)
            _write_bottom_surface(f, width, height)
            _write_top_faces(f, width, height)
            _write_bottom_faces(f, width, height, total)
            _write_side_faces(f, width, height, total)

        if not App.ActiveDocument:
            App.newDocument("CNC_Plate_Project")
        doc = App.ActiveDocument

        mesh_data = Mesh.read(temp_obj_path)
        mesh_obj = doc.addObject("Mesh::Feature", "CNC_Solid_Plate")
        mesh_obj.Mesh = mesh_data

        doc.recompute()
        App.Console.PrintMessage("Плиту для ЧПУ успішно згенеровано!\n")

    except FileNotFoundError:
        App.Console.PrintError(f"Файл не знайдено: {temp_obj_path}\n")
    except PermissionError:
        App.Console.PrintError(f"Немає доступу для запису: {temp_obj_path}\n")
    except Exception as e:
        App.Console.PrintError(f"Помилка: {str(e)}\n")
    finally:
        if os.path.exists(temp_obj_path):
            os.remove(temp_obj_path)


if __name__ == "__main__":
    png_to_solid_plate()
