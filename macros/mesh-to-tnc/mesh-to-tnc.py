import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets, QtGui
import Mesh
import os

DEFAULTS = {
    "program_name": "MESH_CNC",
    "tool_number": 1,
    "tool_diameter": 3.0,
    "spindle_speed": 10000,
    "rapid_feed": 5000,
    "cutting_feed": 800,
    "plunge_feed": 300,
    "safe_height": 5.0,
    "clearance_height": 2.0,
    "scan_step_x": 0.5,
    "scan_step_y": 0.5,
    "output_format": "gcode",
    "output_filename": "mesh_cnc",
}


class _CNCConfigDialog:
    def __init__(self, mesh):
        self._mesh = mesh
        self._result = None
        bbox = mesh.BoundBox
        mesh_info = (
            f"Mesh: X[{bbox.XMin:.1f}, {bbox.XMax:.1f}] "
            f"Y[{bbox.YMin:.1f}, {bbox.YMax:.1f}] "
            f"Z[{bbox.ZMin:.1f}, {bbox.ZMax:.1f}]  "
            f"Points: {len(mesh.Points)}"
        )
        self._dialog = QtWidgets.QDialog()
        self._dialog.setWindowTitle("Налаштування CNC програми")
        self._dialog.setMinimumWidth(480)
        layout = QtWidgets.QVBoxLayout(self._dialog)
        info_label = QtWidgets.QLabel(mesh_info)
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info_label)
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._create_format_tab(), "Формат")
        tabs.addTab(self._create_tool_tab(), "Інструмент")
        tabs.addTab(self._create_feed_tab(), "Подачі")
        tabs.addTab(self._create_scan_tab(), "Сканування")
        tabs.addTab(self._create_height_tab(), "Висоти")
        layout.addWidget(tabs)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("Згенерувати")
        btn_ok.clicked.connect(self._on_accept)
        btn_layout.addWidget(btn_ok)
        btn_cancel = QtWidgets.QPushButton("Скасувати")
        btn_cancel.clicked.connect(self._dialog.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _make_row(self, label, widget):
        row = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(label)
        lbl.setFixedWidth(140)
        row.addWidget(lbl)
        row.addWidget(widget)
        return row

    def _create_format_tab(self):
        tab = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(tab)
        self._combo_format = QtWidgets.QComboBox()
        self._combo_format.addItems(["G-code (CAMotics / LinuxCNC / GRBL)", "Heidenhain TNC"])
        lay.addLayout(self._make_row("Формат:", self._combo_format))
        self._edit_filename = QtWidgets.QLineEdit(DEFAULTS["output_filename"])
        lay.addLayout(self._make_row("Ім'я файлу:", self._edit_filename))
        self._lbl_ext = QtWidgets.QLabel(".gcode")
        self._lbl_ext.setStyleSheet("color: #999;")
        lay.addLayout(self._make_row("Розширення:", self._lbl_ext))
        self._combo_format.currentIndexChanged.connect(self._update_ext)
        lay.addStretch()
        return tab

    def _update_ext(self):
        ext = ".gcode" if self._combo_format.currentIndex() == 0 else ".tnc"
        self._lbl_ext.setText(ext)

    def _create_tool_tab(self):
        tab = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(tab)
        self._spin_tool_num = QtWidgets.QSpinBox()
        self._spin_tool_num.setRange(1, 99)
        self._spin_tool_num.setValue(DEFAULTS["tool_number"])
        lay.addLayout(self._make_row("Номер інструменту:", self._spin_tool_num))
        self._spin_tool_dia = QtWidgets.QDoubleSpinBox()
        self._spin_tool_dia.setRange(0.1, 100.0)
        self._spin_tool_dia.setDecimals(1)
        self._spin_tool_dia.setSuffix(" mm")
        self._spin_tool_dia.setValue(DEFAULTS["tool_diameter"])
        lay.addLayout(self._make_row("Діаметр фрези:", self._spin_tool_dia))
        self._spin_rpm = QtWidgets.QSpinBox()
        self._spin_rpm.setRange(100, 100000)
        self._spin_rpm.setSingleStep(100)
        self._spin_rpm.setSuffix(" об/хв")
        self._spin_rpm.setValue(DEFAULTS["spindle_speed"])
        lay.addLayout(self._make_row("Оберти (RPM):", self._spin_rpm))
        lay.addStretch()
        return tab

    def _create_feed_tab(self):
        tab = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(tab)
        self._spin_rapid = QtWidgets.QSpinBox()
        self._spin_rapid.setRange(100, 50000)
        self._spin_rapid.setSingleStep(100)
        self._spin_rapid.setSuffix(" мм/хв")
        self._spin_rapid.setValue(DEFAULTS["rapid_feed"])
        lay.addLayout(self._make_row("Подача позиц.:", self._spin_rapid))
        self._spin_cutting = QtWidgets.QSpinBox()
        self._spin_cutting.setRange(10, 10000)
        self._spin_cutting.setSingleStep(50)
        self._spin_cutting.setSuffix(" мм/хв")
        self._spin_cutting.setValue(DEFAULTS["cutting_feed"])
        lay.addLayout(self._make_row("Подача різання:", self._spin_cutting))
        self._spin_plunge = QtWidgets.QSpinBox()
        self._spin_plunge.setRange(10, 5000)
        self._spin_plunge.setSingleStep(10)
        self._spin_plunge.setSuffix(" мм/хв")
        self._spin_plunge.setValue(DEFAULTS["plunge_feed"])
        lay.addLayout(self._make_row("Подача занурення:", self._spin_plunge))
        lay.addStretch()
        return tab

    def _create_scan_tab(self):
        tab = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(tab)
        self._spin_step_x = QtWidgets.QDoubleSpinBox()
        self._spin_step_x.setRange(0.05, 20.0)
        self._spin_step_x.setDecimals(2)
        self._spin_step_x.setSuffix(" мм")
        self._spin_step_x.setValue(DEFAULTS["scan_step_x"])
        lay.addLayout(self._make_row("Крок по X:", self._spin_step_x))
        self._spin_step_y = QtWidgets.QDoubleSpinBox()
        self._spin_step_y.setRange(0.05, 20.0)
        self._spin_step_y.setDecimals(2)
        self._spin_step_y.setSuffix(" мм")
        self._spin_step_y.setValue(DEFAULTS["scan_step_y"])
        lay.addLayout(self._make_row("Крок по Y:", self._spin_step_y))
        self._lbl_estimate = QtWidgets.QLabel()
        self._lbl_estimate.setStyleSheet("color: #666; font-size: 11px;")
        lay.addWidget(self._lbl_estimate)
        self._spin_step_x.valueChanged.connect(self._update_estimate)
        self._spin_step_y.valueChanged.connect(self._update_estimate)
        self._update_estimate()
        lay.addStretch()
        return tab

    def _update_estimate(self):
        bbox = self._mesh.BoundBox
        cols = max(1, int((bbox.XMax - bbox.XMin) / self._spin_step_x.value()) + 1)
        rows = max(1, int((bbox.YMax - bbox.YMin) / self._spin_step_y.value()) + 1)
        pts = cols * rows
        self._lbl_estimate.setText(
            f"~{cols} x {rows} = {pts:,} точок  "
            f"({pts * 8 / 1024:.0f} KB RAM, ~{pts * 40 / 1024:.0f} KB файл)"
        )

    def _create_height_tab(self):
        tab = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(tab)
        self._spin_safe = QtWidgets.QDoubleSpinBox()
        self._spin_safe.setRange(0.5, 100.0)
        self._spin_safe.setDecimals(1)
        self._spin_safe.setSuffix(" мм")
        self._spin_safe.setValue(DEFAULTS["safe_height"])
        lay.addLayout(self._make_row("Безпечна висота:", self._spin_safe))
        self._spin_clearance = QtWidgets.QDoubleSpinBox()
        self._spin_clearance.setRange(0.0, 50.0)
        self._spin_clearance.setDecimals(1)
        self._spin_clearance.setSuffix(" мм")
        self._spin_clearance.setValue(DEFAULTS["clearance_height"])
        lay.addLayout(self._make_row("Висота перед plunge:", self._spin_clearance))
        lay.addStretch()
        return tab

    def _on_accept(self):
        fmt = "gcode" if self._combo_format.currentIndex() == 0 else "tnc"
        ext = ".gcode" if fmt == "gcode" else ".tnc"
        default_dir = os.path.expanduser("~/Desktop")
        filename = self._edit_filename.text().strip() or "mesh_cnc"
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, "Зберегти CNC програму",
            os.path.join(default_dir, filename + ext),
            f"CNC файли (*{ext})",
        )
        if not save_path:
            return
        self._result = {
            "program_name": DEFAULTS["program_name"],
            "tool_number": self._spin_tool_num.value(),
            "tool_diameter": self._spin_tool_dia.value(),
            "spindle_speed": self._spin_rpm.value(),
            "rapid_feed": self._spin_rapid.value(),
            "cutting_feed": self._spin_cutting.value(),
            "plunge_feed": self._spin_plunge.value(),
            "safe_height": self._spin_safe.value(),
            "clearance_height": self._spin_clearance.value(),
            "scan_step_x": self._spin_step_x.value(),
            "scan_step_y": self._spin_step_y.value(),
            "output_format": fmt,
            "output_path": save_path,
        }
        self._dialog.accept()

    def run(self):
        self._dialog.exec()
        return self._result


def _get_selected_mesh():
    selection = Gui.Selection.getSelection()
    if not selection:
        App.Console.PrintError("Оберіть об'єкт Mesh у документі.\n")
        return None
    obj = selection[0]
    if hasattr(obj, "Mesh"):
        return obj.Mesh
    if obj.TypeId == "Mesh::Feature":
        return obj.Mesh
    App.Console.PrintError(f"Об'єкт '{obj.Name}' не є Mesh.\n")
    return None


def _get_mesh_bounds(mesh):
    bbox = mesh.BoundBox
    return bbox.XMin, bbox.YMin, bbox.ZMin, bbox.XMax, bbox.YMax, bbox.ZMax


def _build_heightmap(mesh, step_x, step_y):
    x_min, y_min, z_min, x_max, y_max, z_max = _get_mesh_bounds(mesh)
    cols = max(1, int((x_max - x_min) / step_x) + 1)
    rows = max(1, int((y_max - y_min) / step_y) + 1)
    heightmap = [[z_min for _ in range(cols)] for _ in range(rows)]
    for v in mesh.Points:
        col = max(0, min(int((v.x - x_min) / step_x), cols - 1))
        row = max(0, min(int((v.y - y_min) / step_y), rows - 1))
        if v.z > heightmap[row][col]:
            heightmap[row][col] = v.z
    return heightmap, x_min, y_min, cols, rows


def _interpolate_z(heightmap, x, y, x_min, y_min, step_x, step_y, cols, rows):
    fx = (x - x_min) / step_x
    fy = (y - y_min) / step_y
    c0 = max(0, min(int(fx), cols - 2))
    r0 = max(0, min(int(fy), rows - 2))
    tx = fx - c0
    ty = fy - r0
    z00 = heightmap[r0][c0]
    z10 = heightmap[r0][c0 + 1]
    z01 = heightmap[r0 + 1][c0]
    z11 = heightmap[r0 + 1][c0 + 1]
    z0 = z00 + tx * (z10 - z00)
    z1 = z01 + tx * (z11 - z01)
    return z0 + ty * (z1 - z0)


def _fmt_gcode(v):
    return f"{v:.3f}"


def _fmt_tnc(v):
    return f"{'+' if v >= 0 else ''}{v:.3f}"


def _write_gcode(mesh, cfg):
    x_min, y_min, z_min, x_max, y_max, z_max = _get_mesh_bounds(mesh)
    App.Console.PrintMessage(f"Heightmap {cfg['scan_step_x']}x{cfg['scan_step_y']} mm...\n")
    heightmap, hx, hy, cols, rows = _build_heightmap(mesh, cfg["scan_step_x"], cfg["scan_step_y"])
    App.Console.PrintMessage(f"Grid: {cols}x{rows} ({cols*rows} points)\n")
    fmt = _fmt_gcode
    safe = cfg["safe_height"]
    clr = cfg["clearance_height"]
    sx = cfg["scan_step_x"]
    sy = cfg["scan_step_y"]

    with open(cfg["output_path"], "w") as f:
        f.write("%\n")
        f.write(f"O{cfg['program_name']}\n")
        f.write(f"( T{cfg['tool_number']} D{cfg['tool_diameter']}mm S{cfg['spindle_speed']} )\n")
        f.write(f"( Feed: cut={cfg['cutting_feed']} plunge={cfg['plunge_feed']} rapid={cfg['rapid_feed']} )\n")
        f.write(f"( Scan: {sx}x{sy}mm )\n")
        f.write("G21 G90 G17 G40\n")
        f.write(f"G00 Z{fmt(safe)}\n")
        f.write(f"T{cfg['tool_number']} M06\n")
        f.write(f"S{cfg['spindle_speed']} M03\n")
        f.write("G43\n")
        f.write(f"G00 X{fmt(x_min)} Y{fmt(y_min)}\n")

        total = rows
        for row_idx in range(rows):
            y = hy + row_idx * sy
            if row_idx % 2 == 0:
                c_start, c_end, c_step = 0, cols - 1, 1
            else:
                c_start, c_end, c_step = cols - 1, 0, -1

            col = c_start
            x = hx + col * sx
            z = _interpolate_z(heightmap, x, y, hx, hy, sx, sy, cols, rows)
            f.write(f"G00 X{fmt(x)} Y{fmt(y)} Z{fmt(z + clr)}\n")
            f.write(f"G01 Z{fmt(z)} F{cfg['plunge_feed']}\n")

            col += c_step
            while True:
                x = hx + col * sx
                z = _interpolate_z(heightmap, x, y, hx, hy, sx, sy, cols, rows)
                f.write(f"G01 X{fmt(x)} Z{fmt(z)} F{cfg['cutting_feed']}\n")
                if col == c_end:
                    break
                col += c_step

            f.write(f"G00 Z{fmt(safe)}\n")
            if row_idx % 50 == 0:
                App.Console.PrintMessage(f"  Line {row_idx+1}/{total}\n")

        f.write(f"G00 Z{fmt(safe + 10.0)}\n")
        f.write("M05 G49 M30\n%\n")
    App.Console.PrintMessage(f"G-code saved: {cfg['output_path']}\n")


def _write_tnc(mesh, cfg):
    x_min, y_min, z_min, x_max, y_max, z_max = _get_mesh_bounds(mesh)
    App.Console.PrintMessage(f"Heightmap {cfg['scan_step_x']}x{cfg['scan_step_y']} mm...\n")
    heightmap, hx, hy, cols, rows = _build_heightmap(mesh, cfg["scan_step_x"], cfg["scan_step_y"])
    App.Console.PrintMessage(f"Grid: {cols}x{rows} ({cols*rows} points)\n")
    fmt = _fmt_tnc
    safe = cfg["safe_height"]
    clr = cfg["clearance_height"]
    sx = cfg["scan_step_x"]
    sy = cfg["scan_step_y"]

    with open(cfg["output_path"], "w") as f:
        f.write(f"BEGIN PGM {cfg['program_name']} MM\n")
        f.write(f"BLK FORM 0.1 Z {fmt(x_min)} {fmt(y_min)} {fmt(z_min - 1.0)}\n")
        f.write(f"BLK FORM 0.2 {fmt(x_max)} {fmt(y_max)} {fmt(z_max + safe)}\n")
        f.write(f"TOOL CALL {cfg['tool_number']} Z S{cfg['spindle_speed']}\n")
        f.write(f"L Z{fmt(safe)} F{cfg['rapid_feed']} M3\n")

        total = rows
        for row_idx in range(rows):
            y = hy + row_idx * sy
            if row_idx % 2 == 0:
                c_start, c_end, c_step = 0, cols - 1, 1
            else:
                c_start, c_end, c_step = cols - 1, 0, -1

            col = c_start
            x = hx + col * sx
            z = _interpolate_z(heightmap, x, y, hx, hy, sx, sy, cols, rows)
            f.write(f"L X{fmt(x)} Y{fmt(y)} Z{fmt(z + clr)} F{cfg['rapid_feed']}\n")
            f.write(f"L Z{fmt(z)} F{cfg['plunge_feed']}\n")

            col += c_step
            while True:
                x = hx + col * sx
                z = _interpolate_z(heightmap, x, y, hx, hy, sx, sy, cols, rows)
                f.write(f"L X{fmt(x)} Z{fmt(z)} F{cfg['cutting_feed']}\n")
                if col == c_end:
                    break
                col += c_step

            f.write(f"L Z{fmt(safe)} F{cfg['rapid_feed']}\n")
            if row_idx % 50 == 0:
                App.Console.PrintMessage(f"  Line {row_idx+1}/{total}\n")

        f.write(f"L Z{fmt(safe + 10.0)} F{cfg['rapid_feed']}\n")
        f.write("M5\n")
        f.write(f"END PGM {cfg['program_name']} MM\n")
    App.Console.PrintMessage(f"TNC saved: {cfg['output_path']}\n")


def mesh_to_tnc():
    mesh = _get_selected_mesh()
    if mesh is None:
        return
    cfg = _CNCConfigDialog(mesh).run()
    if cfg is None:
        App.Console.PrintMessage("Cancelled.\n")
        return
    try:
        if cfg["output_format"] == "gcode":
            _write_gcode(mesh, cfg)
        else:
            _write_tnc(mesh, cfg)
        App.Console.PrintMessage(f"Done! {cfg['output_path']}\n")
    except PermissionError:
        App.Console.PrintError(f"Cannot write: {cfg['output_path']}\n")
    except MemoryError:
        App.Console.PrintError("Out of memory. Increase SCAN_STEP values.\n")
    except Exception as e:
        App.Console.PrintError(f"Error: {str(e)}\n")


if __name__ == "__main__":
    mesh_to_tnc()
