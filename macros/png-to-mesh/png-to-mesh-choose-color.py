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

# COLOR MODE: "auto" | "light-bg" | "dark-bg" | "custom" | "pick"
#   auto      — analyze histogram, auto-detect background
#   light-bg  — white = surface, black = carved deep
#   dark-bg   — black = surface, white = carved deep
#   custom    — use CUSTOM_MAP below
#   pick      — interactive dialog: click on image to choose surface color
COLOR_MODE = "pick"

# CUSTOM_MAP: list of (brightness, depth_fraction) pairs
# brightness: 0.0 = black, 1.0 = white
# depth_fraction: 0.0 = surface, 1.0 = full carving depth
# Must be sorted by brightness. Linearly interpolated between stops.
# Example: only carve very dark and very bright, mid-tones stay at surface
CUSTOM_MAP = [
    (0.0, 1.0),
    (0.3, 0.0),
    (0.7, 0.0),
    (1.0, 1.0),
]
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


def _compute_brightness(img):
    w, h = img.width(), img.height()
    total_brightness = 0.0
    count = 0
    for y in range(h):
        for x in range(w):
            color = QtGui.QColor(img.pixel(x, y))
            if color.alpha() == 0:
                continue
            b = (color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114) / 255.0
            total_brightness += b
            count += 1
    return total_brightness / count if count > 0 else 0.5


def _detect_color_mode(img):
    avg = _compute_brightness(img)
    if avg > 0.5:
        mode = "light-bg"
        App.Console.PrintMessage(f"Авто-режим: середня яскравість {avg:.2f} > 0.5 → light-bg (білий = поверхня)\n")
    else:
        mode = "dark-bg"
        App.Console.PrintMessage(f"Авто-режим: середня яскравість {avg:.2f} <= 0.5 → dark-bg (чорний = поверхня)\n")
    return mode


def _interpolate_custom_map(brightness):
    if not CUSTOM_MAP:
        return brightness
    if brightness <= CUSTOM_MAP[0][0]:
        return CUSTOM_MAP[0][1]
    if brightness >= CUSTOM_MAP[-1][0]:
        return CUSTOM_MAP[-1][1]
    for i in range(len(CUSTOM_MAP) - 1):
        b0, d0 = CUSTOM_MAP[i]
        b1, d1 = CUSTOM_MAP[i + 1]
        if b0 <= brightness <= b1:
            t = (brightness - b0) / (b1 - b0)
            return d0 + t * (d1 - d0)
    return brightness


def _brightness_to_depth(brightness, color_mode):
    if color_mode == "light-bg":
        return brightness
    elif color_mode == "dark-bg":
        return 1.0 - brightness
    elif color_mode == "custom":
        return _interpolate_custom_map(brightness)
    return brightness


class _ColorPickerDialog:
    def __init__(self, img):
        from PySide import QtCore, QtWidgets

        self._img = img
        self._ref_brightness = None
        self._done = False

        self._pixmap = QtGui.QPixmap.fromImage(img)

        self._dialog = QtWidgets.QDialog()
        self._dialog.setWindowTitle("Оберіть колір поверхні (клацніть на зображенні)")
        self._dialog.setMinimumSize(400, 400)

        layout = QtWidgets.QVBoxLayout(self._dialog)

        self._label = QtWidgets.QLabel()
        self._label.setPixmap(self._pixmap)
        self._label.setAlignment(QtCore.Qt.AlignCenter)
        self._label.setCursor(QtCore.Qt.CrossCursor)
        self._label.mousePressEvent = self._on_click
        layout.addWidget(self._label)

        self._info = QtWidgets.QLabel("Клацніть на піксель — колір стане рівнем поверхні (без глибини)")
        layout.addWidget(self._info)

        self._color_preview = QtWidgets.QLabel()
        self._color_preview.setFixedHeight(30)
        layout.addWidget(self._color_preview)

        btn_layout = QtWidgets.QHBoxLayout()
        self._btn_confirm = QtWidgets.QPushButton("Підтвердити")
        self._btn_confirm.setEnabled(False)
        self._btn_confirm.clicked.connect(self._dialog.accept)
        btn_layout.addWidget(self._btn_confirm)

        self._btn_cancel = QtWidgets.QPushButton("Скасувати")
        self._btn_cancel.clicked.connect(self._dialog.reject)
        btn_layout.addWidget(self._btn_cancel)

        layout.addLayout(btn_layout)

    def _on_click(self, event):
        from PySide import QtCore

        pos = event.position()
        x = pos.x()
        y = pos.y()

        label_size = self._label.size()
        pixmap_size = self._pixmap.size()

        img_x = int(x * pixmap_size.width() / label_size.width())
        img_y = int(y * pixmap_size.height() / label_size.height())

        img_x = max(0, min(img_x, self._img.width() - 1))
        img_y = max(0, min(img_y, self._img.height() - 1))

        color = QtGui.QColor(self._img.pixel(img_x, img_y))
        self._ref_brightness = (
            color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
        ) / 255.0

        hex_color = color.name()
        self._color_preview.setText(
            f"  RGB({color.red()}, {color.green()}, {color.blue()})  "
            f"Яскравість: {self._ref_brightness:.3f}  {hex_color}  "
        )
        self._color_preview.setStyleSheet(f"background-color: {hex_color}; color: {'white' if self._ref_brightness < 0.5 else 'black'};")
        self._btn_confirm.setEnabled(True)
        self._info.setText(
            f"Обрано: {hex_color} — цей колір буде на поверхні (глибина = 0)"
        )

    def run(self):
        result = self._dialog.exec()
        if result and self._ref_brightness is not None:
            return self._ref_brightness
        return None


def _pick_color_and_build_map(img):
    picker = _ColorPickerDialog(img)
    ref = picker.run()
    if ref is None:
        App.Console.PrintMessage("Вибір кольору скасовано. Використовується auto-режим.\n")
        return _detect_color_mode(img)

    max_dist = max(ref, 1.0 - ref)
    if max_dist < 0.01:
        max_dist = 1.0

    def map_fn(brightness):
        return abs(brightness - ref) / max_dist

    App.Console.PrintMessage(
        f"Обрано колір поверхні: яскравість={ref:.3f}. "
        f"Інші кольори картуються за відстанню від нього.\n"
    )
    return map_fn


def _write_obj_header(f):
    f.write("# FreeCAD CNC Plate — auto-generated OBJ\n")


def _write_top_surface(f, img, width, height, color_mode):
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

            if callable(color_mode):
                depth_frac = color_mode(brightness)
            else:
                depth_frac = _brightness_to_depth(brightness, color_mode)
            depth = depth_frac * MAX_CARVING_DEPTH
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

    color_mode = COLOR_MODE
    if color_mode == "auto":
        color_mode = _detect_color_mode(img)
    elif color_mode == "pick":
        color_mode = _pick_color_and_build_map(img)
    if isinstance(color_mode, str):
        App.Console.PrintMessage(f"Режим кольору: {color_mode}\n")
    else:
        App.Console.PrintMessage(f"Режим кольору: pick (інтерактивний)\n")

    width = img.width()
    height = img.height()
    total = width * height

    App.Console.PrintMessage(f"Розмір: {width}x{height} ({width * PIXEL_SIZE:.1f}x{height * PIXEL_SIZE:.1f} mm)\n")

    temp_obj_path = os.path.join(tempfile.gettempdir(), "fc_solid_plate.obj")
    try:
        with open(temp_obj_path, "w") as f:
            _write_obj_header(f)
            _write_top_surface(f, img, width, height, color_mode)
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
