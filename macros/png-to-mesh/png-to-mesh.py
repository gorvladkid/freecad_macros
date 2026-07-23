import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui
import tempfile
import os
import Mesh

def png_to_solid_plate():
    image_path = None
    selection = Gui.Selection.getSelection()
    
    if selection:
        selected_obj = selection[0]
        if hasattr(selected_obj, "ImageFile"):
            image_path = selected_obj.ImageFile
        elif hasattr(selected_obj, "FileName"):
            image_path = selected_obj.FileName

    if not image_path:
        file_dialog = QtGui.QFileDialog.getOpenFileName(None, "Оберіть PNG", "", "Images (*.png *.jpg *.jpeg)")
        image_path = file_dialog[0] if isinstance(file_dialog, tuple) else file_dialog

    if not image_path or not os.path.exists(image_path):
        return

    try:
        img = QtGui.QImage(image_path)
        if img.isNull(): return

        # =========================================================
        # НАЛАШТУВАННЯ ГЛИБИНИ ТА РОЗМІРІВ ДЛЯ ЧПУ (Вказуйте в мм)
        # =========================================================
        max_carving_depth = 9.0   # Максимальна глибина впадин (фрезерування)
        plate_thickness = 10.0    # Загальна товщина плити-заготовки
        pixel_size = 0.25         # Масштаб XY: фізичний розмір одного пікселя в мм
        # =========================================================

        width = img.width()
        height = img.height()
        
        App.Console.PrintMessage(f"Розмір: {width}x{height}. Обчислення плити з впадинами...\n")
        obj_lines = []

        # 1. Створення точок рельєфу (Лицьова сторона)
        # Обертаємо цикл Y (height-1 down to 0), щоб прибрати відзеркалення
        for y in range(height - 1, -1, -1):
            for x in range(width):
                color = QtGui.QColor(img.pixel(x, y))
                
                # Обробка прозорості: якщо піксель прозорий (альфа = 0), вважаємо його білим фоном
                if color.alpha() == 0:
                    brightness = 1.0
                else:
                    brightness = (color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114) / 255.0
                
                # ІНВЕРСІЯ: Темні пікселі йдуть глибше (фрезеруються), білі залишаються на поверхні
                # Z починається від верхньої площини заготовки (plate_thickness) і йде вниз
                depth = (1.0 - brightness) * max_carving_depth
                posZ = plate_thickness - depth
                
                posX = x * pixel_size
                posY = (height - 1 - y) * pixel_size
                
                obj_lines.append(f"v {posX:.4f} {posY:.4f} {posZ:.4f}\n")

        # 2. Створення точок плоского дна плити (Z = 0)
        # Вони дублюють сітку лицьової сторони, але лежать строго на нулі
        for y in range(height - 1, -1, -1):
            for x in range(width):
                posX = x * pixel_size
                posY = (height - 1 - y) * pixel_size
                obj_lines.append(f"v {posX:.4f} {posY:.4f} 0.0000\n")

        # 3. Зшиваємо грані (Faces)
        total_pixels = width * height

        # Лицьова поверхня (впадини логотипу)
        for y in range(height - 1):
            for x in range(width - 1):
                i0 = y * width + x + 1
                i1 = y * width + (x + 1) + 1
                i2 = (y + 1) * width + x + 1
                i3 = (y + 1) * width + (x + 1) + 1
                obj_lines.append(f"f {i0} {i3} {i1}\n")
                obj_lines.append(f"f {i0} {i2} {i3}\n")

        # Нижня поверхня (абсолютно плоске дно заготовки)
        for y in range(height - 1):
            for x in range(width - 1):
                i0 = y * width + x + 1 + total_pixels
                i1 = y * width + (x + 1) + 1 + total_pixels
                i2 = (y + 1) * width + x + 1 + total_pixels
                i3 = (y + 1) * width + (x + 1) + 1 + total_pixels
                obj_lines.append(f"f {i0} {i1} {i3}\n")
                obj_lines.append(f"f {i0} {i3} {i2}\n")

        # Бічні стінки плити (закриваємо контур, щоб меш став Solid)
        # Ліва і права стінки
        for y in range(height - 1):
            # Ліва стінка (x = 0)
            w0 = y * width + 1
            w1 = (y + 1) * width + 1
            b0 = w0 + total_pixels
            b1 = w1 + total_pixels
            obj_lines.append(f"f {w0} {b0} {b1}\n")
            obj_lines.append(f"f {w0} {b1} {w1}\n")
            
            # Права стінка (x = width - 1)
            w0 = y * width + width
            w1 = (y + 1) * width + width
            b0 = w0 + total_pixels
            b1 = w1 + total_pixels
            obj_lines.append(f"f {w0} {b1} {b0}\n")
            obj_lines.append(f"f {w0} {w1} {b1}\n")

        # Передня і задня стінки
        for x in range(width - 1):
            # Нижня стінка по екрану (y = 0)
            w0 = x + 1
            w1 = (x + 1) + 1
            b0 = w0 + total_pixels
            b1 = w1 + total_pixels
            obj_lines.append(f"f {w0} {b1} {b0}\n")
            obj_lines.append(f"f {w0} {w1} {b1}\n")

            # Верхня стінка по екрану (y = height - 1)
            w0 = (height - 1) * width + x + 1
            w1 = (height - 1) * width + (x + 1) + 1
            b0 = w0 + total_pixels
            b1 = w1 + total_pixels
            obj_lines.append(f"f {w0} {b0} {b1}\n")
            obj_lines.append(f"f {w0} {b1} {w1}\n")

        # Збереження та завантаження у FreeCAD
        temp_dir = tempfile.gettempdir()
        temp_obj_path = os.path.join(temp_dir, "fc_solid_plate.obj")
        with open(temp_obj_path, "w") as f:
            f.writelines(obj_lines)

        if not App.ActiveDocument: App.newDocument("CNC_Plate_Project")
        doc = App.ActiveDocument

        loaded_mesh_data = Mesh.read(temp_obj_path)
        mesh_obj = doc.addObject("Mesh::Feature", "CNC_Solid_Plate")
        mesh_obj.Mesh = loaded_mesh_data
        
        os.remove(temp_obj_path)
        doc.recompute()
        App.Console.PrintMessage("Плиту для ЧПУ успішно згенеровано!\n")

    except Exception as e:
        App.Console.PrintError(f"Помилка: {str(e)}\n")

png_to_solid_plate()
