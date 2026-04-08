import sys

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QIntValidator
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtGui import QDoubleValidator
from skyfield.api import load, Loader
from skyfield.toposlib import wgs84
from datetime import timedelta
from pytz import timezone
from skyfield.units import Angle
from random import randint
from collections import deque
from os import remove, path

def isfloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

data_save = 2

lang = 0
lang_list = []
lang_all_list = ["rus", "eng"]

theme = 0
theme_all_list = ["dark", "light"]

for i in lang_all_list:
    with open(f"language/{i}.txt", "r", encoding='utf-8') as file:
        lang_list.append(list(map(str.strip, file.readlines())))

with open(f"data/save.txt", "r", encoding='utf-8') as file:
    save = list(map(str.strip, file.readlines()))
    if len(save) > 0 and save[0] in lang_all_list:
        lang = lang_all_list.index(save[0])
    if len(save) > 1 and save[1] in theme_all_list:
        theme = theme_all_list.index(save[1])

def save_file():
    with open("data/save.txt", "w+", encoding='utf-8') as file:
        new_save = list(map(str.strip, file.readlines()))
        for i in range(data_save - len(new_save)):
            new_save += [""]
        new_save[0] = lang_all_list[lang]
        new_save[1] = theme_all_list[theme]
        for item in new_save:
            file.write(f"{item}\n")

class MainGraphicView(QtWidgets.QGraphicsView):
    base_coords_out_signal = QtCore.pyqtSignal(float, float)
    base_change_signal = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.SCALE_FACTOR = 1.25
        self.scene = QtWidgets.QGraphicsScene()
        self.img = QtWidgets.QGraphicsPixmapItem()
        self.img.setPixmap(QtGui.QPixmap("texture/worldmap.png"))
        self.scene.addItem(self.img)
        self.setScene(self.scene)

        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.zoom_value = 0
        self.reset_view(int(self.SCALE_FACTOR ** self.zoom_value))
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.x_pix = 3840
        self.y_pix = 1920
        self.lon_pix = self.x_pix / 360
        self.lat_pix = self.y_pix / 180
        self.pix_mid_lon = self.x_pix / 2
        self.pix_mid_lat = self.y_pix / 2

        self.start_lon = 30.31410
        self.start_lat = 59.93860

        self.pic_size = 60
        self.pic_size_2 = self.pic_size // 2
        self.pic_sat = QtWidgets.QGraphicsPixmapItem()
        self.pic_sat.setPixmap(QtGui.QPixmap('texture/sat.png').scaled(self.pic_size, self.pic_size))
        self.scene.addItem(self.pic_sat)
        self.pic_base = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap('texture/base.png').scaled(self.pic_size, self.pic_size, ))

        self.color_base_list = []
        self.pic_base_list = []
        self.index = 0
        self.add_base(randint(0, 255), randint(0, 255), randint(0, 255))

        self.scene.installEventFilter(self)
        self.setMouseTracking(True)

        self.list_lines = []

    def change_color(self, r: int, g: int, b: int):
        new_color = self.color_base_list[self.index]
        new_color.setColor(QtGui.QColor(r, g, b))
        self.color_base_list[self.index] = new_color

    def change_index(self, number):
        self.index = number

    def add_base(self, r: int, g: int, b: int):
        new_pic_base = self.pic_base.pixmap()
        self.pic_base_list.append(QtWidgets.QGraphicsPixmapItem(new_pic_base))
        self.index = len(self.pic_base_list) -1
        new_color = QtWidgets.QGraphicsColorizeEffect()
        new_color.setStrength(1.0)
        new_color.setColor(QtGui.QColor(r, g, b))
        self.color_base_list.append(new_color)
        self.pic_base_list[self.index].setGraphicsEffect(new_color)
        self.scene.addItem(self.pic_base_list[self.index])

    def del_base(self):
        self.scene.removeItem(self.pic_base_list[self.index])
        self.color_base_list.pop(self.index)
        self.pic_base_list.pop(self.index)

    def draw_line_by_geo(self, lat1, lon1, lat2, lon2, color):
        pen = QtGui.QPen(color)
        x1, y1 = self.geo_to_pix(lat1, lon1)
        x2, y2 = self.geo_to_pix(lat2, lon2)
        if abs(x1 - x2) < self.x_pix / 2:
            self.list_lines.append(self.scene.addLine(x1, y1, x2, y2, pen))
        else:
            if x1 > x2:
                x3 = x2 + self.x_pix
                x4 = x1 - self.x_pix
                self.list_lines.append(self.scene.addLine(x1, y1, x3, y2, pen))
                self.list_lines.append(self.scene.addLine(x2, y2, x4, y1, pen))
            else:
                x3 = x2 - self.x_pix
                x4 = x1 + self.x_pix
                self.list_lines.append(self.scene.addLine(x1, y1, x3, y2, pen))
                self.list_lines.append(self.scene.addLine(x2, y2, x4, y1, pen))

    def clear_lines(self):
        for i in self.list_lines:
            self.scene.removeItem(i)
        self.list_lines = []

    def eventFilter(self, source, event):
        if len(self.pic_base_list) != 0:
            if event.type() == QtCore.QEvent.Type.GraphicsSceneMousePress:
                item = self.scene.itemAt(event.scenePos(), QtGui.QTransform())
                if event.button() == QtCore.Qt.MouseButton.RightButton:
                    if isinstance(item, QtWidgets.QGraphicsPixmapItem) and (item == self.img or item == self.pic_base_list[self.index]):
                        map_coords = item.mapFromScene(event.scenePos())
                        if item == self.pic_base_list[self.index]:
                            gcoo = self.geo_to_pix(self.start_lat, self.start_lon)
                            map_coords = QPointF(gcoo[0], gcoo[1])
                        geocoo = self.pix_to_geo(map_coords.x(), map_coords.y())
                        self.base_coords_out_signal.emit(geocoo[0], geocoo[1])
                        self.move_base_to(map_coords.x(), map_coords.y())
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    if isinstance(item, QtWidgets.QGraphicsPixmapItem) and item != self.img:
                        index = self.pic_base_list.index(item)
                        self.change_index(index)
                        self.base_change_signal.emit(index)
        return super().eventFilter(source, event)

    def move_base_to(self, lat: float, lon: float):
        self.pic_base_list[self.index].setPos(lat - self.pic_size_2, lon - self.pic_size_2)

    def move_sat_to(self, lat, lon):
        sat_x, sat_y = self.geo_to_pix(lat, lon)
        sat_x -= self.pic_size_2
        sat_y -= self.pic_size_2
        self.pic_sat.setPos(sat_x, sat_y)

    def geo_to_pix(self, lat, lon):
        x = (lon + 180) * self.lon_pix
        y = (90 - lat) * self.lat_pix
        return x, y

    def pix_to_geo(self, x, y):
        lon = x / self.lon_pix - 180
        lat = 90 - y / self.lat_pix
        return lat, lon

    def reset_view(self, scale=1):
        rect = QtCore.QRectF(self.img.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if (scale := max(1, scale)) == 1:
                self.zoom_value = 0
            unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
            self.scale(1 / unity.width(), 1 / unity.height())
            viewrect = self.viewport().rect()
            scenerect = self.transform().mapRect(rect)
            factor = min(viewrect.width() / scenerect.width(),
                         viewrect.height() / scenerect.height()) * scale
            self.scale(factor, factor)

    def zoom(self, step):
        zoom = max(0, self.zoom_value + (step := int(step)))
        if zoom != self.zoom_value:
            self.zoom_value = zoom
            if self.zoom_value > 0:
                if step > 0:
                    factor = self.SCALE_FACTOR ** step
                else:
                    factor = 1 / self.SCALE_FACTOR ** abs(step)
                self.scale(factor, factor)
            else:
                self.reset_view()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.zoom(delta and delta // abs(delta))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reset_view()



class SettingsWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{lang_list[lang][41]}")

        self.button_setting = QtWidgets.QPushButton(f"{lang_list[lang][41]}")
        self.button_setting.setFixedWidth(100)

        main_layout = QtWidgets.QFormLayout()

        lang_label = QtWidgets.QLabel(f"{lang_list[lang][37]}: ")
        self.lang_box = QtWidgets.QComboBox()
        lang_name_list = ["Русский", "English"]
        self.lang_box.addItems(lang_name_list)
        self.lang_box.setCurrentIndex(lang)

        theme_label = QtWidgets.QLabel(f"{lang_list[lang][40]}")
        self.theme_box = QtWidgets.QComboBox()
        theme_list = [f"{lang_list[lang][43]}", f"{lang_list[lang][44]}"]
        self.theme_box.addItems(theme_list)
        self.theme_box.setCurrentIndex(theme)

        update_tle_label = QtWidgets.QLabel(f"{lang_list[lang][42]}")
        self.update_tle_button = QtWidgets.QPushButton(f"{lang_list[lang][45]}")


        main_layout.addRow(lang_label, self.lang_box)
        main_layout.addRow(theme_label, self.theme_box)
        # main_layout.addRow(update_tle_label, self.update_tle_button)
        # TLE file updates are not working yet

        self.setLayout(main_layout)

    def change_lang(self, index):
        global lang
        lang = index
        save_file()
        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle(f"{lang_list[lang][38]}")
        main_layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel(f"{lang_list[lang][39]}")
        main_layout.addWidget(label)
        dlg.setLayout(main_layout)
        dlg.exec()

class ColorWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{lang_list[lang][4]}")
        color_layout = QtWidgets.QVBoxLayout()
        button_layout = QtWidgets.QHBoxLayout()
        random_layout = QtWidgets.QHBoxLayout()
        red_layout = QtWidgets.QHBoxLayout()
        green_layout = QtWidgets.QHBoxLayout()
        blue_layout = QtWidgets.QHBoxLayout()
        red_label = QtWidgets.QLabel(f"{lang_list[lang][5]}: ")
        green_label = QtWidgets.QLabel(f"{lang_list[lang][6]}: ")
        blue_label = QtWidgets.QLabel(f"{lang_list[lang][7]}: ")
        random_label = QtWidgets.QLabel(f"{lang_list[lang][8]}: ")
        self.finish_button = QtWidgets.QPushButton(f"{lang_list[lang][9]}")
        self.cancel_button = QtWidgets.QPushButton(f"{lang_list[lang][10]}")
        self.random_check = QtWidgets.QCheckBox()
        self.random_check.setCheckState(QtCore.Qt.CheckState.Checked)
        self.red_line = QtWidgets.QLineEdit("0")
        self.green_line = QtWidgets.QLineEdit("0")
        self.blue_line = QtWidgets.QLineEdit("0")

        color_line_validator = QIntValidator(0, 255)
        self.red_line.setValidator(color_line_validator)
        self.green_line.setValidator(color_line_validator)
        self.blue_line.setValidator(color_line_validator)

        color_layout.addLayout(red_layout)
        color_layout.addLayout(green_layout)
        color_layout.addLayout(blue_layout)
        color_layout.addLayout(random_layout)
        color_layout.addLayout(button_layout)
        button_layout.addWidget(self.finish_button)
        button_layout.addWidget(self.cancel_button)
        red_layout.addWidget(red_label)
        red_layout.addWidget(self.red_line)
        green_layout.addWidget(green_label)
        green_layout.addWidget(self.green_line)
        blue_layout.addWidget(blue_label)
        blue_layout.addWidget(self.blue_line)
        random_layout.addWidget(random_label)
        random_layout.addWidget(self.random_check)

        self.setLayout(color_layout)

    def set_name(self, name):
        self.setWindowTitle(f"{name}")

class ColorBase(ColorWindow):
    def __init__(self):
        super().__init__()

class ColorSat(ColorWindow):
    def __init__(self):
        super().__init__()
        self.random_check.setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.setWindowTitle(f"{lang_list[lang][36]}")
        self.red_line.setText("255")
        self.green_line.setText("30")
        self.blue_line.setText("20")



class ListWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QtWidgets.QVBoxLayout()
        title_label = QtWidgets.QLabel(f"{lang_list[lang][16]}")
        self.sessions_list = QtWidgets.QListWidget()
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.sessions_list)
        self.setLayout(main_layout)

class ParametersWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QtWidgets.QVBoxLayout()
        button_layaot = QtWidgets.QHBoxLayout()

        title_label = QtWidgets.QLabel(f"{lang_list[lang][11]}")

        time_layout = QtWidgets.QHBoxLayout()
        self.time_line = QtWidgets.QLineEdit()
        time_line_validator = QIntValidator(0, 999)
        self.time_line.setText("7")
        self.time_line.setValidator(time_line_validator)
        self.time_label = QtWidgets.QLabel(f"{lang_list[lang][12]}: ")
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.time_line)

        degree_layout = QtWidgets.QHBoxLayout()
        degree_line_validator = QDoubleValidator(0, 90, 2)
        degree_line_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        degree_line_validator.setLocale(QtCore.QLocale("en_US"))
        self.degree_line = QtWidgets.QLineEdit()
        self.degree_line.setText("30")
        self.degree_line.setValidator(degree_line_validator)
        self.degree_label = QtWidgets.QLabel(f"{lang_list[lang][13]}: ")
        degree_layout.addWidget(self.degree_label)
        degree_layout.addWidget(self.degree_line)

        self.start_button = QtWidgets.QPushButton(f"{lang_list[lang][14]}")
        self.clear_button = QtWidgets.QPushButton(f"{lang_list[lang][15]}")

        main_layout.addWidget(title_label)
        main_layout.addLayout(time_layout)
        main_layout.addLayout(degree_layout)
        main_layout.addLayout(button_layaot)
        button_layaot.addWidget(self.start_button)
        button_layaot.addWidget(self.clear_button)

        self.setLayout(main_layout)

class ComCenterWidget(QtWidgets.QWidget):
    def __init__(self, start_lon: float, start_lat: float):
        super().__init__()
        self.lat = float(start_lat)
        self.lon = float(start_lon)
        lat_dms = Angle(degrees=self.lat)
        lon_dms = Angle(degrees=self.lon)
        self.base_list = [[self.lat, self.lon]]

        main_layout = QtWidgets.QVBoxLayout()
        title_layout = QtWidgets.QHBoxLayout()
        title_label = QtWidgets.QLabel(f"{lang_list[lang][0]}:")
        button_layout = QtWidgets.QHBoxLayout()
        self.base_box = QtWidgets.QComboBox()
        self.base_box.addItem(f"{lang_list[lang][1]}")
        self.color_base = QtWidgets.QPushButton()
        self.color_base.setStyleSheet(f"background-color: rgb({0, 0, 0});")
        self.add_button = QtWidgets.QPushButton(f"{lang_list[lang][2]}")
        self.delete_button = QtWidgets.QPushButton(f"{lang_list[lang][3]}")
        self.color_button = QtWidgets.QPushButton(f"{lang_list[lang][4]}")
        self.base_box.setEditable(True)
        self.base_box.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.base_box.completer().setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)

        lat_layout = QtWidgets.QFormLayout()
        lat_deg_layout = QtWidgets.QHBoxLayout()
        lat_label = QtWidgets.QLabel("Lat: ")
        self.lat_line = QtWidgets.QLineEdit(f"{self.lat}")
        self.lat_line.setMaximumWidth(100)
        self.lat_deg_label = QtWidgets.QLabel(f"            {lat_dms}")
        lon_layout = QtWidgets.QFormLayout()
        lon_deg_layout = QtWidgets.QHBoxLayout()
        lon_label = QtWidgets.QLabel("Lon: ")
        self.lon_line = QtWidgets.QLineEdit(f"{self.lon}")
        self.lon_line.setMaximumWidth(100)
        self.lon_deg_label = QtWidgets.QLabel(f"            {lon_dms}")

        lat_validator = QDoubleValidator(-99.99999, 99.99999, 5)
        lat_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        lat_validator.setLocale(QtCore.QLocale("en_US"))
        self.lat_line.setValidator(lat_validator)
        lon_validator = QDoubleValidator(-999.99999, 999.99999, 5)
        lon_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        lon_validator.setLocale(QtCore.QLocale("en_US"))
        self.lon_line.setValidator(lon_validator)

        main_layout.addLayout(title_layout)
        main_layout.addLayout(button_layout)
        main_layout.addLayout(lat_layout)
        main_layout.addLayout(lat_deg_layout)
        main_layout.addLayout(lon_layout)
        main_layout.addLayout(lon_deg_layout)
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.base_box)
        title_layout.addWidget(self.color_base)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.color_button)
        lat_layout.addRow(lat_label, self.lat_line)
        lat_deg_layout.addWidget(self.lat_deg_label)
        lon_layout.addRow(lon_label, self.lon_line)
        lon_deg_layout.addWidget(self.lon_deg_label)

        self.setLayout(main_layout)

    def change_color(self, r: int = 0, g: int = 0, b: int = 0):
        self.color_base.setStyleSheet(f"background-color: rgb({r}, {g}, {b});")

    def show_coords(self, lat: float, lon: float):
        self.base_list[self.base_box.currentIndex()] = [lat, lon]
        self.lat = f'{lat:.5f}'
        lat_deg = str(Angle(degrees= float(self.lat)))
        self.lon = f"{lon:.5f}"
        lon_deg = str(Angle(degrees= float(self.lon)))
        self.lat_line.setText(f"{self.lat.rstrip("0").rstrip(".")}")
        if lat < 0:
            self.lat_deg_label.setText(f"South   {lat_deg}")
        else:
            self.lat_deg_label.setText(f"North   {lat_deg}")
        self.lon_line.setText(f'{self.lon.rstrip("0").rstrip(".")}')
        if lon < 0:
            self.lon_deg_label.setText(f"West    {lon_deg}")
        else:
            self.lon_deg_label.setText(f"East    {lon_deg}")

    def get_coords(self):
        return self.lat, self.lon

    def remove_index(self, index):
        self.base_box.removeItem(index)

    def change_index(self, index):
        self.base_box.setCurrentIndex(index)

class SpacecraftWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QtWidgets.QVBoxLayout()
        title_layout = QtWidgets.QHBoxLayout()
        satellite_time_layout = QtWidgets.QFormLayout()
        latlon_layout = QtWidgets.QVBoxLayout()
        lat_layout = QtWidgets.QFormLayout()
        lon_layout = QtWidgets.QFormLayout()
        color_layout = QtWidgets.QVBoxLayout()
        self.current_sattelite = "ISS (ZARYA)"
        self.satellites_box = QtWidgets.QComboBox()
        self.download_tle_file()
        self.satellites_box.setEditable(True)
        self.satellites_box.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.satellites_box.completer().setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self.button_update = QtWidgets.QPushButton(f"{lang_list[lang][17]}")

        latlon_label = QtWidgets.QLabel(f"{lang_list[lang][20]}:")
        self.lat_label = QtWidgets.QLabel("LAT: ")
        self.lat_deg_label = QtWidgets.QLabel("")
        self.lat_deg_direction_label = QtWidgets.QLabel("")
        self.lon_label = QtWidgets.QLabel("LON: ")
        self.lon_deg_label = QtWidgets.QLabel("")
        self.lon_deg_direction_label = QtWidgets.QLabel("")

        self.color_path = QtWidgets.QPushButton()
        self.color_path.setStyleSheet(f"background-color: rgb({0, 0, 0});")
        self.color_button = QtWidgets.QPushButton(f"{lang_list[lang][21]}")
        self.hour_line = QtWidgets.QLineEdit("24")

        self.hour_line.setMaximumWidth(50)
        self.satellites_box.setMaximumWidth(200)

        self.hour_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        validator = QIntValidator(1, 999)
        self.hour_line.setValidator(validator)

        main_layout.addLayout(satellite_time_layout)
        main_layout.addLayout(title_layout)
        title_layout.addLayout(latlon_layout)
        title_layout.addLayout(color_layout)
        satellite_time_layout.addRow(f"{lang_list[lang][18]}:", self.satellites_box)
        satellite_time_layout.addRow(f"{lang_list[lang][19]}:", self.hour_line)
        latlon_layout.addWidget(latlon_label)
        latlon_layout.addLayout(lat_layout)
        latlon_layout.addLayout(lon_layout)
        lat_layout.addRow("Lat:", self.lat_label)
        lat_layout.addRow(self.lat_deg_direction_label, self.lat_deg_label)
        lon_layout.addRow("Lon:", self.lon_label)
        lon_layout.addRow(self.lon_deg_direction_label, self.lon_deg_label)
        color_layout.addWidget(self.color_path)
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.button_update)

        self.setLayout(main_layout)

    def download_tle_file(self, update = False):
        load = Loader('data')
        satellites_url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
        self.satellites_file = load.tle_file(satellites_url)
        self.by_name = {sat.name: sat for sat in self.satellites_file}
        self.satellites = list(self.by_name.keys())
        self.satellites.sort()
        self.satellites_box.clear()
        self.satellites_box.addItems(self.satellites)
        if self.current_sattelite in self.satellites:
            self.satellites_box.setCurrentText(self.current_sattelite)
        else:
            self.satellites_box.setCurrentIndex(0)

    def change_color(self, r: int = 0, g: int = 0, b: int = 0):
        self.color_path.setStyleSheet(f"background-color: rgb({r}, {g}, {b});")

    def show_coords(self, lat, lon):
        self.lat_label.setText(f"{lat}")
        self.lon_label.setText(f"{lon}")
        lat_deg = Angle(degrees=lat)
        lon_deg = Angle(degrees=lon)
        if lat < 0:
            self.lat_deg_label.setText(f"{lat_deg}")
            self.lat_deg_direction_label.setText("South")
        else:
            self.lat_deg_label.setText(f"{lat_deg}")
            self.lat_deg_direction_label.setText("North")
        if lon < 0:
            self.lon_deg_label.setText(f"{lon_deg}")
            self.lon_deg_direction_label.setText("West")
        else:
            self.lon_deg_label.setText(f"{lon_deg}")
            self.lon_deg_direction_label.setText("East")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        icon = QtGui.QIcon("texture/icon.ico")
        self.setWindowTitle("Satellite routes")
        self.setWindowIcon(icon)

        self.satellite = None
        self.queue = None
        self.time = None

        self.g_viewer = MainGraphicView()
        self.spacecraft_w = SpacecraftWidget()
        self.parameters_w = ParametersWidget()
        self.setting_w = SettingsWindow()
        self.color_w_base = ColorBase()
        self.color_w_sat = ColorSat()

        self.second = 30
        self.timer = QtCore.QTimer(self)
        self.timer.start(self.second * 1000)
        self.timer.timeout.connect(self.update_coordinates)
        self.count = int(self.spacecraft_w.hour_line.text()) * 60 * 60 // self.second

        self.queue = deque(maxlen=self.count)

        self.r_sat = int(self.color_w_sat.red_line.text())
        self.g_sat = int(self.color_w_sat.green_line.text())
        self.b_sat = int(self.color_w_sat.blue_line.text())
        self.color = QtGui.QColor(self.r_sat, self.g_sat, self.b_sat)

        self.g_viewer.base_coords_out_signal.connect(self.base_coords_handler)
        self.g_viewer.base_change_signal.connect(self.base_change_handler)

        self.com_center_w = ComCenterWidget(self.g_viewer.start_lon, self.g_viewer.start_lat)
        self.com_center_w.base_box.currentIndexChanged.connect(self.change_base)
        self.com_center_w.add_button.clicked.connect(self.add_button_clicked)
        self.com_center_w.delete_button.clicked.connect(self.delete_button_clicked)
        self.com_center_w.color_button.clicked.connect(self.show_color_base)
        self.com_center_w.lat_line.editingFinished.connect(self.base_show)
        self.com_center_w.lon_line.editingFinished.connect(self.base_show)

        self.spacecraft_w.hour_line.editingFinished.connect(self.sat_show)
        self.spacecraft_w.satellites_box.textActivated.connect(self.sat_show)
        self.spacecraft_w.button_update.clicked.connect(self.sat_show)
        self.spacecraft_w.color_button.clicked.connect(self.show_color_sat)

        self.parameters_w.start_button.clicked.connect(self.start_button_clicked)
        self.parameters_w.clear_button.clicked.connect(self.clear_button_clicked)

        self.color_w_base.finish_button.clicked.connect(self.color_change_base)
        self.color_w_base.cancel_button.clicked.connect(self.color_cancel_base)
        self.color_w_sat.finish_button.clicked.connect(self.color_change_sat)
        self.color_w_sat.cancel_button.clicked.connect(self.color_cancel_sat)

        self.setting_w.button_setting.clicked.connect(self.setting_show)
        self.setting_w.lang_box.textActivated.connect(self.change_lang)
        self.setting_w.theme_box.textActivated.connect(self.toggle_theme)
        self.setting_w.update_tle_button.clicked.connect(self.update_tle_file)

        self.list_w = ListWidget()

        window_widget = QtWidgets.QWidget()

        main_layout = QtWidgets.QHBoxLayout()
        list_layout = QtWidgets.QVBoxLayout()
        big_layout = QtWidgets.QVBoxLayout()
        info_layout = QtWidgets.QHBoxLayout()
        setting_layout = QtWidgets.QVBoxLayout()
        mgv_layout = QtWidgets.QHBoxLayout()

        setting_layout.addWidget(self.setting_w.button_setting)

        info_layout.addWidget(self.com_center_w, 2)
        info_layout.addWidget(self.spacecraft_w, 2)
        info_layout.addWidget(self.parameters_w, 2)

        mgv_layout.addWidget(self.g_viewer)
        list_layout.addWidget(self.list_w)
        big_layout.addLayout(setting_layout, 1)
        big_layout.addLayout(mgv_layout, 20)
        big_layout.addLayout(info_layout, 4)

        main_layout.addLayout(big_layout, 3)
        main_layout.addLayout(list_layout, 1)
        window_widget.setLayout(main_layout)

        self.color_change_base()
        self.setCentralWidget(window_widget)
        self.spacecraft_w.change_color(self.r_sat, self.g_sat, self.b_sat)
        self.toggle_theme()

        self.base_show()
        self.sat_show()


    @QtCore.pyqtSlot()
    def start_button_clicked(self):
        error = []
        peak_t = None
        start_t_str = None
        if len(self.g_viewer.pic_base_list) == 0:
            error.append(f"{lang_list[lang][22]}")
        for i in range(len(self.com_center_w.base_list)):
            if not isfloat(self.com_center_w.base_list[i][0]):
                error.append(f"{lang_list[lang][23]}")
            if not isfloat(self.com_center_w.base_list[i][1]):
                error.append(f"{lang_list[lang][24]}")
            if not self.parameters_w.time_line.text().isnumeric():
                error.append(f"{lang_list[lang][25]}")
            if not isfloat(self.parameters_w.degree_line.text()):
                error.append(f"{lang_list[lang][26]}")
            elif float(self.parameters_w.degree_line.text()) > 90:
                error.append(f"{lang_list[lang][26]}")
            if len(error) == 0:
                td = int(self.parameters_w.time_line.text())
                degrees = float(self.parameters_w.degree_line.text())
                t0 = self.time
                t1 = self.time + timedelta(days=td)
                stp = wgs84.latlon(self.com_center_w.base_list[i][0], self.com_center_w.base_list[i][1])
                dif = self.satellite - stp
                te, ev = self.satellite.find_events(stp, t0, t1, altitude_degrees=degrees)
                start_t, finish_t, top = None, None, None
                no_events = True
                for ti, event in zip(te, ev):
                    if event == 0:
                        start_t = ti.astimezone(timezone('Europe/Moscow'))
                        start_t_str = start_t.strftime('%H:%M:%S')
                    if event == 1:
                        peak_t = ti.astimezone(timezone('Europe/Moscow')).strftime('%Y %b %d %H:%M:%S')
                        top = dif.at(ti)
                    if event == 2:
                        finish_t = ti.astimezone(timezone('Europe/Moscow'))
                        finish_t_str = finish_t.strftime('%H:%M:%S')
                        alt, az, dist = top.altaz()
                        dif_t_str = (finish_t - start_t)
                        text = (f'{lang_list[lang][1]}: {self.com_center_w.base_box.itemText(i)}\n'
                                f'\t{lang_list[lang][27]} (UTC+3): {peak_t}\n'
                                f'\t{lang_list[lang][28]}:\t{az}\n'
                                f'\t{lang_list[lang][29]}:\t{alt}\n'                           
                                f'\t{lang_list[lang][30]}:\t{start_t_str}\n'
                                f'\t{lang_list[lang][31]}:\t{finish_t_str}\n'
                                f'\t{lang_list[lang][32]}:\t{dif_t_str}')
                        self.list_w.sessions_list.addItem(text)
                        no_events = False
                if no_events:
                    self.list_w.sessions_list.addItem(f"{lang_list[lang][33]} {self.com_center_w.base_box.itemText(i)}")

        if len(error) > 0:
            dlg = QtWidgets.QDialog(self)
            dlg.setWindowTitle(f"{lang_list[lang][34]}")
            main_layout = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel(f"{lang_list[lang][35]}:")
            main_layout.addWidget(label)
            for i in range(len(error)):
                label_error = QtWidgets.QLabel(f"{error[i]}")
                main_layout.addWidget(label_error)
            dlg.setLayout(main_layout)
            dlg.exec()

    def clear_button_clicked(self):
        self.list_w.sessions_list.clear()


    def base_show(self):
        if isfloat(self.com_center_w.lat_line.text()):
            lat = float(self.com_center_w.lat_line.text())
            if lat > 90:
                lat = 90
            if -90 > lat:
                lat = -90
        else:
            lat = 0
        if isfloat(self.com_center_w.lon_line.text()):
            lon = float(self.com_center_w.lon_line.text())
            if lon > 180:
                lon = 180
            if -180 > lon:
                lon = -180
        else:
            lon = 0

        self.com_center_w.base_list[self.g_viewer.index] = [lat, lon]
        pix_lat, pix_lon = self.g_viewer.geo_to_pix(lat, lon)
        self.com_center_w.show_coords(lat, lon)
        self.g_viewer.move_base_to(pix_lat, pix_lon)

    def base_coords_handler(self, lat: float = 0, lon: float = 0):
        if self.g_viewer.pic_base_list != 0:
            self.com_center_w.show_coords(lat, lon)

    def base_change_handler(self, index: int):
        self.com_center_w.base_box.setCurrentIndex(index)
        self.change_base()

    def change_base(self):
        if len(self.g_viewer.pic_base_list) == 0:
            lat = 0
            lon = 0
            self.com_center_w.change_color(0, 0, 0)
        else:
            self.g_viewer.change_index(self.com_center_w.base_box.currentIndex())
            lat = self.com_center_w.base_list[self.g_viewer.index][0]
            lon = self.com_center_w.base_list[self.g_viewer.index][1]
            pix_lat, pix_lon = self.g_viewer.geo_to_pix(lat, lon)
            self.g_viewer.move_base_to(pix_lat, pix_lon)
        self.change_rgb_base()
        self.com_center_w.show_coords(lat, lon)

    def add_button_clicked(self):
        if self.com_center_w.base_box.findText(self.com_center_w.base_box.currentText()) == -1:
            self.g_viewer.add_base(randint(0, 255), randint(0, 255), randint(0, 255))
            self.color_change_base()
            self.com_center_w.base_box.addItem(self.com_center_w.base_box.currentText())
            self.com_center_w.base_list.append([self.g_viewer.start_lat, self.g_viewer.start_lon])
            self.com_center_w.change_index(self.g_viewer.index)
            lat = self.g_viewer.start_lat
            lon = self.g_viewer.start_lon
            pix_lat, pix_lon = self.g_viewer.geo_to_pix(lat, lon)
            self.com_center_w.show_coords(lat, lon)
            self.g_viewer.move_base_to(pix_lat, pix_lon)
        # else:
        #     self.com_center_w.com_box.addItem(f"{self.com_center_w.com_box.count()+1}")
        #     self.com_center_w.com_list.append(self.start_pos)
        #     lat = self.com_center_w.com_list[self.com_center_w.com_box.currentIndex()][0]
        #     lon = self.com_center_w.com_list[self.com_center_w.com_box.currentIndex()][1]
        #     pix_lat, pix_lon = self.g_viewer.geo_to_pix(lat, lon)
        #     self.com_center_w.show_coords(lat, lon)
        #     self.g_viewer.move_base_to(pix_lat, pix_lon)

    def delete_button_clicked(self):
        if len(self.g_viewer.pic_base_list) > 1:
            self.g_viewer.del_base()
            self.com_center_w.base_list.pop(self.g_viewer.index)
            self.com_center_w.remove_index(self.g_viewer.index)
            self.change_base()
            #I don't know how to allow the deletion of all НПУ so that the program does not crash.
            #I succeeded once, but the change of НПУ after deletion did not work correctly.

    def show_color_base(self):
        self.change_rgb_base()
        self.color_w_base.set_name(self.com_center_w.base_box.currentText())
        self.color_w_base.show()

    def color_change_base(self):
        if self.color_w_base.random_check.checkState() == QtCore.Qt.CheckState.Checked:
            r = randint(0, 255)
            g = randint(0, 255)
            b = randint(0, 255)
        else:
            r = int(self.color_w_base.red_line.text())
            g = int(self.color_w_base.green_line.text())
            b = int(self.color_w_base.blue_line.text())
        self.g_viewer.change_color(r, g, b)
        self.change_rgb_base()

    def color_cancel_base(self):
        self.change_rgb_base()

    def get_rgb_base(self):
        r, g, b, a = self.g_viewer.color_base_list[self.g_viewer.index].color().getRgb()
        return r, g, b

    def change_rgb_base(self):
        r, g, b = self.get_rgb_base()
        self.color_w_base.red_line.setText(f"{r}")
        self.color_w_base.green_line.setText(f"{g}")
        self.color_w_base.blue_line.setText(f"{b}")
        self.com_center_w.change_color(r, g, b)

    def change_name(self):
        self.queue.clear()
        self.sat_show()


    def sat_show(self):
        self.g_viewer.clear_lines()
        self.count = int(self.spacecraft_w.hour_line.text()) * 60 * 60 // self.second
        self.queue = deque(maxlen=self.count)
        self.r_sat = int(self.color_w_sat.red_line.text())
        self.g_sat = int(self.color_w_sat.green_line.text())
        self.b_sat = int(self.color_w_sat.blue_line.text())
        self.color = QtGui.QColor(self.r_sat, self.g_sat, self.b_sat)
        satellite_name = self.spacecraft_w.satellites_box.currentText()
        self.spacecraft_w.current_sattelite = satellite_name
        queue = self.get_satellite_path_coordinates(satellite_name).copy()
        x, y = self.get_satellite_coordinates(satellite_name)
        self.spacecraft_w.show_coords(x, y)
        self.g_viewer.move_sat_to(x, y)
        x1, y1 = queue.popleft()
        self.g_viewer.draw_line_by_geo(x, y, x1, y1, self.color)
        while len(queue) > 0:
            x2, y2 = queue.popleft()
            self.g_viewer.draw_line_by_geo(x1, y1, x2, y2, self.color)
            x1 = x2
            y1 = y2

    def update_tle_file(self):
        self.spacecraft_w.download_tle_file(True)
        self.sat_show()

    def show_color_sat(self):
        self.color_w_sat.show()

    def color_cancel_sat(self):
        self.change_rgb_sat()

    def color_change_sat(self):
        if self.color_w_sat.random_check.checkState() == QtCore.Qt.CheckState.Checked:
            self.r_sat = randint(0, 255)
            self.g_sat = randint(0, 255)
            self.b_sat = randint(0, 255)
        else:
            self.r_sat = int(self.color_w_sat.red_line.text())
            self.g_sat = int(self.color_w_sat.green_line.text())
            self.b_sat = int(self.color_w_sat.blue_line.text())
        self.spacecraft_w.change_color(self.r_sat ,self.g_sat, self.b_sat)
        self.change_rgb_sat()
        self.sat_show()

    def change_rgb_sat(self):
        self.color_w_sat.red_line.setText(str(self.r_sat))
        self.color_w_sat.green_line.setText(str(self.g_sat))
        self.color_w_sat.blue_line.setText(str(self.b_sat))

    def get_satellite_coordinates(self, name):
        ts = load.timescale()
        t = ts.now()
        self.time = t
        ts = load.timescale()
        t = ts.now()
        satellite = self.spacecraft_w.by_name[name]
        self.satellite = satellite
        geocentric = satellite.at(t)
        lat_satellite, lon_satellite = wgs84.latlon_of(geocentric)
        return lat_satellite.degrees, lon_satellite.degrees

    def get_satellite_path_coordinates(self, name):
        ts = load.timescale()
        t = ts.now()
        self.time = t
        satellite = self.spacecraft_w.by_name[name]
        if len(self.queue) == 0:
            while len(self.queue) != self.count:
                t += timedelta(seconds=self.second)
                geocentric = satellite.at(t)
                lat_satellite, lon_satellite = wgs84.latlon_of(geocentric)
                self.queue.append([lat_satellite.degrees, lon_satellite.degrees])
        else:
            t += timedelta(seconds=self.second)
            geocentric = satellite.at(t)
            lat_satellite, lon_satellite = wgs84.latlon_of(geocentric)
            self.queue.popleft()
            self.queue.append([lat_satellite.degrees, lon_satellite.degrees])
        return self.queue

    def update_coordinates(self):
        if len(self.queue) != 0:
            self.queue.popleft()
            self.sat_show()

    def setting_show(self):
        self.setting_w.show()

    def change_lang(self):
        self.setting_w.change_lang(self.setting_w.lang_box.currentIndex())

    def toggle_theme(self):
        global theme
        if self.setting_w.theme_box.currentIndex() == 0:
            new_scheme = Qt.ColorScheme.Dark
            theme = 0
        elif self.setting_w.theme_box.currentIndex() == 1:
            new_scheme = Qt.ColorScheme.Light
            theme = 1
        else:
            new_scheme = Qt.ColorScheme.Dark
            theme = 0
        app.styleHints().setColorScheme(new_scheme)
        save_file()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    app.exec()
# auto-py-to-exe