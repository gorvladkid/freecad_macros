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
OUTPUT_WIDTH = 256.0      # desired mesh width in mm (X axis)
OUTPUT_HEIGHT = 256.0     # desired mesh height in mm (Y axis)
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
        self._result = None

        self._pixmap = QtGui.QPixmap.fromImage(img)

        self._dialog = QtWidgets.QDialog()
        self._dialog.setWindowTitle("Налаштування плити")
        self._dialog.setMinimumSize(600, 500)

        main_layout = QtWidgets.QHBoxLayout(self._dialog)

        left = QtWidgets.QVBoxLayout()
        self._label = QtWidgets.QLabel()
        self._label.setPixmap(self._pixmap.scaled(
            350, 350, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        ))
        self._label.setAlignment(QtCore.Qt.AlignCenter)
        self._label.setCursor(QtCore.Qt.CrossCursor)
        self._label.mousePressEvent = self._on_click
        left.addWidget(self._label)

        self._info = QtWidgets.QLabel("Клацніть на піксель — колір стане поверхнею")
        left.addWidget(self._info)

        self._color_preview = QtWidgets.QLabel()
        self._color_preview.setFixedHeight(25)
        left.addWidget(self._color_preview)

        main_layout.addLayout(left)

        right = QtWidgets.QVBoxLayout()

        right.addWidget(QtWidgets.QLabel("Параметри плити:"))

        self._spin_depth = self._make_spin(right, "Макс. глибина (мм):", 0.1, 100.0, 1, MAX_CARVING_DEPTH)
        self._spin_thickness = self._make_spin(right, "Товщина заготовки (мм):", 1.0, 500.0, 1, PLATE_THICKNESS)
        self._spin_width = self._make_spin(right, "Ширина X (мм):", 1.0, 2000.0, 1, OUTPUT_WIDTH)
        self._spin_height = self._make_spin(right, "Висота Y (мм):", 1.0, 2000.0, 1, OUTPUT_HEIGHT)

        right.addSpacing(10)
        right.addWidget(QtWidgets.QLabel("Інформація:"))
        self._lbl_size = QtWidgets.QLabel()
        self._lbl_size.setStyleSheet("color: #666; font-size: 11px;")
        right.addWidget(self._lbl_size)

        self._update_size_info()
        self._spin_width.valueChanged.connect(self._update_size_info)
        self._spin_height.valueChanged.connect(self._update_size_info)

        right.addStretch()
        main_layout.addLayout(right)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Згенерувати")
        btn_ok.clicked.connect(self._on_accept)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QtWidgets.QPushButton("Скасувати")
        btn_cancel.clicked.connect(self._dialog.reject)
        btn_layout.addWidget(btn_cancel)
        right.addLayout(btn_layout)

    def _make_spin(self, layout, label, min_val, max_val, decimals, default):
        from PySide import QtWidgets
        row = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(label)
        lbl.setFixedWidth(160)
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setSuffix(" мм")
        spin.setValue(default)
        row.addWidget(lbl)
        row.addWidget(spin)
        layout.addLayout(row)
        if not hasattr(self, "_spins"):
            self._spins = []
        self._spins.append(spin)
        return spin

    def _update_size_info(self):
        w = self._spin_width.value()
        h = self._spin_height.value()
        px = w / self._img.width()
        py = h / self._img.height()
        self._lbl_size.setText(
            f"Зображення: {self._img.width()}x{self._img.height()} px\n"
            f"Плита: {w:.1f}x{h:.1f} mm\n"
            f"Крок: {px:.4f}x{py:.4f} mm/px"
        )

    def _on_click(self, event):
        pos = event.position()
        label_size = self._label.size()
        pixmap_size = self._pixmap.size()

        img_x = int(pos.x() * pixmap_size.width() / label_size.width())
        img_y = int(pos.y() * pixmap_size.height() / label_size.height())
        img_x = max(0, min(img_x, self._img.width() - 1))
        img_y = max(0, min(img_y, self._img.height() - 1))

        color = QtGui.QColor(self._img.pixel(img_x, img_y))
        self._ref_brightness = (
            color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114
        ) / 255.0

        hex_color = color.name()
        self._color_preview.setText(
            f"  RGB({color.red()}, {color.green()}, {color.blue()})  "
            f"Яскравість: {self._ref_brightness:.3f}  {hex_color}"
        )
        self._color_preview.setStyleSheet(
            f"background-color: {hex_color}; color: {'white' if self._ref_brightness < 0.5 else 'black'};"
        )
        self._info.setText(f"Обрано: {hex_color} — цей колір буде на поверхні (глибина = 0)")

    def _on_accept(self):
        if self._ref_brightness is None:
            self._info.setText("Спочатку оберіть колір на зображенні!")
            return
        self._result = {
            "ref_brightness": self._ref_brightness,
            "max_depth": self._spin_depth.value(),
            "thickness": self._spin_thickness.value(),
            "width_mm": self._spin_width.value(),
            "height_mm": self._spin_height.value(),
        }
        self._dialog.accept()

    def run(self):
        self._dialog.exec()
        return self._result


def _pick_color_and_build_map(img):
    picker = _ColorPickerDialog(img)
    result = picker.run()
    if result is None:
        App.Console.PrintMessage("Скасовано. Використовується auto-режим.\n")
        return None, None

    ref = result["ref_brightness"]
    max_dist = max(ref, 1.0 - ref)
    if max_dist < 0.01:
        max_dist = 1.0

    def map_fn(brightness):
        return abs(brightness - ref) / max_dist

    App.Console.PrintMessage(
        f"Обрано колір поверхні: яскравість={ref:.3f}\n"
    )
    return map_fn, result


def _write_obj_header(f):
    f.write("# FreeCAD CNC Plate — auto-generated OBJ\n")


def _calc_placement(img_w, img_h, out_w, out_h):
    img_aspect = img_w / img_h
    board_aspect = out_w / out_h
    if img_aspect > board_aspect:
        placed_w = out_w
        placed_h = out_w / img_aspect
    else:
        placed_h = out_h
        placed_w = out_h * img_aspect
    offset_x = (out_w - placed_w) / 2
    offset_y = (out_h - placed_h) / 2
    return offset_x, offset_y, placed_w, placed_h


def _write_top_surface(f, img, board_cols, board_rows, color_mode, pixel_x, pixel_y,
                       offset_x, offset_y, img_w, img_h, max_depth, plate_thickness):
    for row in range(board_rows):
        for col in range(board_cols):
            posX = col * pixel_x
            posY = row * pixel_y
            img_x = int((posX - offset_x) / pixel_x + 0.5)
            img_y = int((posY - offset_y) / pixel_y + 0.5)
            if 0 <= img_x < img_w and 0 <= img_y < img_h:
                color = QtGui.QColor(img.pixel(img_x, img_y))
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
                depth = depth_frac * max_depth
                posZ = plate_thickness - depth
            else:
                posZ = plate_thickness
            f.write(f"v {posX:.4f} {posY:.4f} {posZ:.4f}\n")


def _write_bottom_surface(f, board_cols, board_rows, pixel_x, pixel_y):
    for row in range(board_rows):
        for col in range(board_cols):
            posX = col * pixel_x
            posY = row * pixel_y
            f.write(f"v {posX:.4f} {posY:.4f} 0.0000\n")


def _idx_top(row, col, cols):
    return row * cols + col + 1


def _idx_bot(row, col, cols, total_top):
    return total_top + row * cols + col + 1


def _write_top_faces(f, cols, rows):
    for row in range(rows - 1):
        for col in range(cols - 1):
            i0 = _idx_top(row, col, cols)
            i1 = _idx_top(row, col + 1, cols)
            i2 = _idx_top(row + 1, col, cols)
            i3 = _idx_top(row + 1, col + 1, cols)
            f.write(f"f {i0} {i1} {i3}\n")
            f.write(f"f {i0} {i3} {i2}\n")


def _write_bottom_faces(f, cols, rows, total_top):
    for row in range(rows - 1):
        for col in range(cols - 1):
            i0 = _idx_bot(row, col, cols, total_top)
            i1 = _idx_bot(row, col + 1, cols, total_top)
            i2 = _idx_bot(row + 1, col, cols, total_top)
            i3 = _idx_bot(row + 1, col + 1, cols, total_top)
            f.write(f"f {i0} {i3} {i1}\n")
            f.write(f"f {i0} {i2} {i3}\n")


def _write_side_faces(f, cols, rows, total_top):
    for row in range(rows - 1):
        wt = _idx_top(row, 0, cols)
        wb = _idx_top(row + 1, 0, cols)
        bt = _idx_bot(row, 0, cols, total_top)
        bb = _idx_bot(row + 1, 0, cols, total_top)
        f.write(f"f {wt} {bt} {bb}\n")
        f.write(f"f {wt} {bb} {wb}\n")

        wt = _idx_top(row, cols - 1, cols)
        wb = _idx_top(row + 1, cols - 1, cols)
        bt = _idx_bot(row, cols - 1, cols, total_top)
        bb = _idx_bot(row + 1, cols - 1, cols, total_top)
        f.write(f"f {wt} {bb} {bt}\n")
        f.write(f"f {wt} {wb} {bb}\n")

    for col in range(cols - 1):
        wt = _idx_top(0, col, cols)
        wb = _idx_top(0, col + 1, cols)
        bt = _idx_bot(0, col, cols, total_top)
        bb = _idx_bot(0, col + 1, cols, total_top)
        f.write(f"f {wt} {bb} {bt}\n")
        f.write(f"f {wt} {wb} {bb}\n")

        wt = _idx_top(rows - 1, col, cols)
        wb = _idx_top(rows - 1, col + 1, cols)
        bt = _idx_bot(rows - 1, col, cols, total_top)
        bb = _idx_bot(rows - 1, col + 1, cols, total_top)
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
    params = None

    if color_mode == "auto":
        color_mode = _detect_color_mode(img)
    elif color_mode == "pick":
        color_mode, params = _pick_color_and_build_map(img)
        if color_mode is None:
            color_mode = _detect_color_mode(img)
            params = None

    if isinstance(color_mode, str):
        App.Console.PrintMessage(f"Режим кольору: {color_mode}\n")
    else:
        App.Console.PrintMessage(f"Режим кольору: pick (інтерактивний)\n")

    if params:
        max_depth = params["max_depth"]
        plate_thickness = params["thickness"]
        out_w = params["width_mm"]
        out_h = params["height_mm"]
    else:
        max_depth = MAX_CARVING_DEPTH
        plate_thickness = PLATE_THICKNESS
        out_w = OUTPUT_WIDTH
        out_h = OUTPUT_HEIGHT

    width = img.width()
    height = img.height()

    offset_x, offset_y, placed_w, placed_h = _calc_placement(width, height, out_w, out_h)
    pixel_x = placed_w / width
    pixel_y = placed_h / height
    cols = int(round(out_w / pixel_x)) + 1
    rows = int(round(out_h / pixel_y)) + 1
    total_top = cols * rows

    App.Console.PrintMessage(
        f"Зображення: {width}x{height} px\n"
        f"Плита: {out_w:.1f}x{out_h:.1f} mm, товщина {plate_thickness:.1f} mm\n"
        f"Зображення на пластині: {placed_w:.1f}x{placed_h:.1f} mm "
        f"(зміщення {offset_x:.1f}, {offset_y:.1f})\n"
        f"Глибина: {max_depth:.1f} mm, крок {pixel_x:.4f}x{pixel_y:.4f} mm/px\n"
    )

    temp_obj_path = os.path.join(tempfile.gettempdir(), "fc_solid_plate.obj")
    try:
        with open(temp_obj_path, "w") as f:
            _write_obj_header(f)
            _write_top_surface(f, img, cols, rows, color_mode, pixel_x, pixel_y,
                               offset_x, offset_y, width, height, max_depth, plate_thickness)
            _write_bottom_surface(f, cols, rows, pixel_x, pixel_y)
            _write_top_faces(f, cols, rows)
            _write_bottom_faces(f, cols, rows, total_top)
            _write_side_faces(f, cols, rows, total_top)

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
