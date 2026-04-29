import sys
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import os

class MapTool(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Map → Game Converter")
        self.resize(1900, 900)
        base_path = os.path.dirname(__file__)
        self.label = QLabel(self)
        self.pixmap = QPixmap(os.path.join(base_path,"EnrouteMap.png" ))  # ← tu imagen
        self.pixmap = self.pixmap.scaled(1900, 900,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.label.setPixmap(self.pixmap)
        self.label.resize(self.pixmap.size())

        # 🔥 puntos de referencia (CAMBIA ESTO)
        # mapa
        self.mx1, self.my1 = 141, 414
        self.mx2, self.my2 = 750, 244

        # juego
        self.gx1, self.gy1 = -43379, -2337
        self.gx2, self.gy2 = 17527, -20131

        # calcular escala
        self.scale_x = (self.gx2 - self.gx1) / (self.mx2 - self.mx1)
        self.scale_y = (self.gy2 - self.gy1) / (self.my2 - self.my1)

    def mousePressEvent(self, event):
        mx = event.pos().x()
        my = event.pos().y()

        gx, gy = self.map_to_game(mx, my)

        print(f"Mapa: ({mx}, {my}) → Juego: ({gx:.2f}, {gy:.2f})")

    def map_to_game(self, mx, my):
        gx = self.gx1 + (mx - self.mx1) * self.scale_x

        # ⚠️ invierte Y si hace falta
        gy = self.gy1 + (my - self.my1) * self.scale_y

        return gx, gy


app = QApplication(sys.argv)
window = MapTool()
window.show()
sys.exit(app.exec_())