import sys

from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator
from skyfield.api import load
from skyfield.toposlib import wgs84
from skyfield.units import Angle
from datetime import timedelta
from collections import deque

class MainGraphicView(QtWidgets.QGraphicsView):
    def __init__(self):
        super().__init__()
        self.SCALE_FACTOR = 1.25
        self.scene = QtWidgets.QGraphicsScene()
        self.img = QtWidgets.QGraphicsPixmapItem()
        self.img.setPixmap(QtGui.QPixmap("worldmap.png"))
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

        self.pic_size = 120
        self.pic_size_2 = self.pic_size // 2
        self.pic_sat = QtWidgets.QGraphicsPixmapItem()
        self.pic_sat.setPixmap(QtGui.QPixmap('sat.png').scaled(self.pic_size, self.pic_size))
        self.scene.addItem(self.pic_sat)

        self.scene.installEventFilter(self)
        self.setMouseTracking(True)

        self.list_lines = []

    def draw_line_by_geo(self, lon1, lat1, lon2, lat2, color):
        pen = QtGui.QPen(color)
        x1, y1 = self.geo_to_pix(lon1, lat1)
        x2, y2 = self.geo_to_pix(lon2, lat2)
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

    def move_sat_to(self, lon, lat):
        sat_x, sat_y = self.geo_to_pix(lon, lat)
        sat_x -= self.pic_size_2
        sat_y -= self.pic_size_2
        self.pic_sat.setPos(sat_x, sat_y)

    def geo_to_pix(self, lon, lat):
        x = lon * self.lon_pix
        x = self.pix_mid_lon + x
        y = lat * self.lat_pix
        y = self.pix_mid_lat - y
        return x, y

    def pix_to_geo(self, x, y):
        lat = 90 - (y / self.lat_pix)
        lon = x / self.lon_pix
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
            # self.updateCoordinates()

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


class SpacecraftWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QtWidgets.QHBoxLayout()
        satellite_time_layout = QtWidgets.QFormLayout()
        latlon_layout = QtWidgets.QFormLayout()
        color_layout = QtWidgets.QFormLayout()

        self.satellites_url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
        self.satellites = load.tle_file(self.satellites_url)
        self.by_name = {sat.name: sat for sat in self.satellites}
        with open('gp.php') as gp:
            lines = gp.readlines()
            self.satellites = []
            for i in range(0, len(lines), 3):
                name = lines[i].strip('\n').strip()
                self.satellites.append(name)
        self.satellites.sort()
        self.satellites_box = QtWidgets.QComboBox()
        self.satellites_box.addItems(self.satellites)
        self.satellites_box.setCurrentText('POLYTECH-UNIVERSE 3 (R*)')
        self.satellites_box.setMaximumWidth(200)

        self.lat_label = QtWidgets.QLabel()
        self.lon_label = QtWidgets.QLabel()
        self.lat_deg_label = QtWidgets.QLabel()
        self.lon_deg_label = QtWidgets.QLabel()

        self.hour_line = QtWidgets.QLineEdit("48")
        self.red_line = QtWidgets.QLineEdit("255")
        self.green_line = QtWidgets.QLineEdit("30")
        self.blue_line = QtWidgets.QLineEdit("20")

        self.hour_line.setMaximumWidth(50)
        self.red_line.setMaximumWidth(50)
        self.green_line.setMaximumWidth(50)
        self.blue_line.setMaximumWidth(50)

        self.hour_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.red_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.green_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.blue_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        validator = QIntValidator(1, 999)
        validator_color = QIntValidator(0, 255)
        self.hour_line.setValidator(validator)
        self.red_line.setValidator(validator_color)
        self.green_line.setValidator(validator_color)
        self.blue_line.setValidator(validator_color)

        main_layout.addLayout(satellite_time_layout, 3)
        main_layout.addLayout(latlon_layout, 2)
        main_layout.addLayout(color_layout, 6)
        satellite_time_layout.addRow("Спутник:", self.satellites_box)
        satellite_time_layout.addRow("Отрисовка трассы спутника, в часах:", self.hour_line)
        latlon_layout.addRow("Координаты:", None)
        latlon_layout.addRow("Lat:", self.lat_label)
        latlon_layout.addRow("", self.lat_deg_label)
        latlon_layout.addRow("Lon:", self.lon_label)
        latlon_layout.addRow("", self.lon_deg_label)
        color_layout.addRow("Цвет трассы:", None)
        color_layout.addRow("Красный:", self.red_line)
        color_layout.addRow("Зелёный:", self.green_line)
        color_layout.addRow("Синий:", self.blue_line)



        self.setLayout(main_layout)

    def show_coords(self, lon, lat):
        self.lat_label.setText(f"{lat}")
        self.lat_deg_label.setText(f"{Angle(degrees=lat)}")
        self.lon_label.setText(f"{lon}")
        self.lon_deg_label.setText(f"{Angle(degrees=lon)}")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        icon = QtGui.QIcon("icon.ico")
        self.setWindowTitle("Трасса спутника")
        self.setWindowIcon(icon)
        self.satellite = None
        self.queue = None
        self.g_viewer = MainGraphicView()
        self.spacecraft_w = SpacecraftWidget()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_coordinates)
        self.second = 30
        self.count = int(self.spacecraft_w.hour_line.text()) * 60 * 60 // self.second
        self.queue = deque(maxlen= self.count)
        self.timer.start(self.second * 1000)
        self.spacecraft_w.satellites_box.currentTextChanged.connect(self.change_name)
        self.r_sat = int(self.spacecraft_w.red_line.text())
        self.g_sat = int(self.spacecraft_w.green_line.text())
        self.b_sat = int(self.spacecraft_w.blue_line.text())
        self.spacecraft_w.hour_line.editingFinished.connect(self.sat_show)
        self.spacecraft_w.red_line.editingFinished.connect(self.sat_show)
        self.spacecraft_w.green_line.editingFinished.connect(self.sat_show)
        self.spacecraft_w.blue_line.editingFinished.connect(self.sat_show)
        self.color = QtGui.QColor(self.r_sat, self.g_sat, self.b_sat)

        window_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout()
        big_layout = QtWidgets.QVBoxLayout()
        info_layout = QtWidgets.QHBoxLayout()
        mgv_layout = QtWidgets.QHBoxLayout()

        info_layout.addWidget(self.spacecraft_w)
        mgv_layout.addWidget(self.g_viewer)
        big_layout.addLayout(info_layout, 1)
        big_layout.addLayout(mgv_layout, 9)


        main_layout.addLayout(big_layout)
        window_widget.setLayout(main_layout)

        self.setCentralWidget(window_widget)
        self.sat_show()

    @QtCore.pyqtSlot()
    def sat_show(self):
        self.g_viewer.clear_lines()
        self.count = int(self.spacecraft_w.hour_line.text()) * 60 * 60 // self.second
        self.queue = deque(maxlen=self.count)
        self.r_sat = int(self.spacecraft_w.red_line.text())
        self.g_sat = int(self.spacecraft_w.green_line.text())
        self.b_sat = int(self.spacecraft_w.blue_line.text())
        self.color = QtGui.QColor(self.r_sat, self.g_sat, self.b_sat)
        satellite_name = self.spacecraft_w.satellites_box.currentText()
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

    def get_satellite_coordinates(self, name):
        ts = load.timescale()
        t = ts.now()
        satellite = self.spacecraft_w.by_name[name]
        self.satellite = satellite
        geocentric = satellite.at(t)
        lat_satellite, lon_satellite = wgs84.latlon_of(geocentric)
        return lon_satellite.degrees, lat_satellite.degrees

    def get_satellite_path_coordinates(self, name):
        ts = load.timescale()
        t1 = ts.now()
        satellite = self.spacecraft_w.by_name[name]
        if len(self.queue) == 0:
            while len(self.queue) != self.count :
                t1 += timedelta(seconds=self.second)
                geocentric = satellite.at(t1)
                lat_satellite, lon_satellite = wgs84.latlon_of(geocentric)
                self.queue.append([lon_satellite.degrees, lat_satellite.degrees])
        else:
            t1 += timedelta(seconds=self.count * self.second)
            geocentric = satellite.at(t1)
            lat_satellite, lon_satellite = wgs84.latlon_of(geocentric)
            self.queue.popleft()
            self.queue.append([lon_satellite.degrees, lat_satellite.degrees])


        return self.queue

    def change_name(self):
        self.queue.clear()
        self.sat_show()

    def update_coordinates(self):
        if len(self.queue) != 0:
            self.queue.popleft()
            self.queue.popleft()
            self.sat_show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    app.exec()
