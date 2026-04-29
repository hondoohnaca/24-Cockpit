import sys
import os
import json
import asyncio
import threading
import keyboard
import websockets
import time
import math
import json

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QLineEdit
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QRegExp, QPoint
from PyQt5.QtGui import QPixmap, QTransform,QPainter ,QDoubleValidator, QRegExpValidator,QPen, QColor



class Estado:
    modo_edicion = True

def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS  
    return os.path.dirname(os.path.abspath(__file__))  

base_path = get_base_path()
ruta = os.path.join(base_path, "Data")




class DataBus(QObject):
    updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.altitud = 0
        self.last_altitude = 0
        self.velocidad = 0
        self.player = "JondoOnaca"
        self.last_time = time.time()
        self.delta_time = 0 
        self.position = {"x":0, "y":0}
        self.n1 = 0
        self.n2 = 0
        self.ground_speed = 0

        base_path = ruta
        
        with open(os.path.join(base_path, "VorDic.txt"), "r", encoding="utf-8") as vor_json:
            self.vors = json.load(vor_json)
        


    def set_data(self, data):
        self.last_altitude = self.altitud
        self.altitud = data.get("altitude", 0)
        
        self.velocidad = data.get("speed", 0)

        new_time = time.time()
        self.delta_time =  new_time - self.last_time
        self.last_time = new_time

        self.position = data.get("position",0)

        self.ground_speed = data.get("groundSpeed",0)


        self.updated.emit()

    def set_player(self,player):
        self.player = player

bus = DataBus()


class WSClient:
    def __init__(self, bus):
        self.bus = bus

    async def connect(self):
        uri = "wss://24data.ptfs.app/wss"

        while True:  
            try:
                async with websockets.connect(uri) as websocket:
                    print("WS conectado")

                    while True:
                        msg = await websocket.recv()
                        all_player_data = json.loads(msg)

                        if all_player_data.get("t") != "ACFT_DATA":
                            continue

                        all_player_data = all_player_data["d"]

                        data = None

                        for plane_id, player_data in all_player_data.items():
                            if player_data.get("playerName") == self.bus.player:
                                player_data["ACFT_Name"] = plane_id
                                data = player_data
                                break

                        if data:
                            self.bus.set_data(data)

            except Exception as e:
                print("WS error, reconectando:", e)
                await asyncio.sleep(2)


def start_ws(bus):
    asyncio.run(WSClient(bus).connect())


threading.Thread(target=start_ws, args=(bus,), daemon=True).start()



class Altimetro(QWidget):
    def __init__(self, bus):
        super().__init__()
        self.ready = False
        self.bus = bus
        self.offset = None
        self.size = 300
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint|Qt.Tool)
        self.resize(self.size, self.size)

        base_path = ruta


        self.fondo = QLabel(self)

        self.fondo_pixmap = QPixmap(os.path.join(base_path, "AltimetroBase.png"))
        self.fondo_pixmap = self.fondo_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.fondo.setPixmap(self.fondo_pixmap)
        self.fondo.resize(self.size, self.size)


        self.aguja_100 = QLabel(self)

        self.aguja_100_pixmap = QPixmap(os.path.join(base_path, "AltimetroAguja100.png"))
        self.aguja_100_pixmap = self.aguja_100_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.aguja_100.resize(self.size, self.size)



        self.aguja_1000 = QLabel(self)

        self.aguja_1000_pixmap = QPixmap(os.path.join(base_path, "AltimetroAguja1000.png"))
        self.aguja_1000_pixmap = self.aguja_1000_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.aguja_1000.resize(self.size, self.size)

        self.aguja_10000 = QLabel(self)

        self.aguja_10000_pixmap = QPixmap(os.path.join(base_path, "AltimetroAguja10000.png"))
        self.aguja_10000_pixmap = self.aguja_10000_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.aguja_10000.resize(self.size, self.size)



        self.bus.altitud = 0
        self.actualizar()
        self.bus.updated.connect(self.actualizar)
        
    def draw_needle(self, painter, pixmap, angle):
        painter.save()

        center = self.size / 2

        painter.translate(center, center)
        painter.rotate(angle)
        painter.translate(-center, -center)


        painter.drawPixmap(0, 0, pixmap)

        painter.restore()


    def actualizar(self):
        if not self.isVisible() and self.ready:
            return
        self.ready = True
        alt = self.bus.altitud

        angulo100 = (alt / 1000) * 360
        angulo1000 = (alt / 10000) * 360
        angulo10000 = (alt / 100000) * 360

        final = QPixmap(self.size, self.size)
        final.fill(Qt.transparent)

        painter = QPainter(final)


        self.draw_needle(painter, self.aguja_10000_pixmap, angulo10000)
        self.draw_needle(painter, self.aguja_1000_pixmap, angulo1000)
        self.draw_needle(painter, self.aguja_100_pixmap, angulo100)

        painter.end()

        self.aguja_100.setPixmap(final)


    def mousePressEvent(self, event):
        if Estado.modo_edicion:
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if Estado.modo_edicion and self.offset:
            self.move(self.pos() + event.pos() - self.offset)

class VerticalSpeedIndicatior(QWidget):
    def __init__(self, bus):
        super().__init__()
        self.ready = False
        self.bus = bus
        self.offset = None
        self.size = 300
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint|Qt.Tool)
        self.resize(self.size, self.size)

        base_path = ruta


        self.fondo = QLabel(self)

        self.fondo_pixmap = QPixmap(os.path.join(base_path, "VISBase.png"))
        self.fondo_pixmap = self.fondo_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.fondo.setPixmap(self.fondo_pixmap)
        self.fondo.resize(self.size, self.size)


        self.aguja = QLabel(self)

        self.aguja_pixmap = QPixmap(os.path.join(base_path, "VISBAguja.png"))
        self.aguja_pixmap = self.aguja_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.aguja.resize(self.size, self.size)





        self.bus.altitud = 0
        self.actualizar()
        self.bus.updated.connect(self.actualizar)
        
    def draw_needle(self, painter, pixmap, angle):
        painter.save()

        center = self.size / 2

        painter.translate(center, center)
        painter.rotate(angle)
        painter.translate(-center, -center)


        painter.drawPixmap(0, 0, pixmap)

        painter.restore()


    def actualizar(self):

        if not self.isVisible() and self.ready:
            return
        self.ready = True
        altitude_variation = 0
        if bus.delta_time != 0:
            altitude_variation = (bus.altitud-bus.last_altitude)*60/(100*bus.delta_time)   
        
        angulo = 0
        
        if altitude_variation > 20:
            symbol = 1
            if altitude_variation < 0:
                symbol = -1
            angulo = 168*symbol
        else:
            angulo =(altitude_variation*168)/20

        final = QPixmap(self.size, self.size)
        final.fill(Qt.transparent)

        painter = QPainter(final)


        self.draw_needle(painter, self.aguja_pixmap, angulo)


        painter.end()

        self.aguja.setPixmap(final)
    def mousePressEvent(self, event):
        if Estado.modo_edicion:
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if Estado.modo_edicion and self.offset:
            self.move(self.pos() + event.pos() - self.offset)
class Vor_1(QWidget,):
    def __init__(self, bus,N):
        super().__init__()

        self.indicator_angle = 0

        self.ready = False
        self.bus = bus
        self.offset = None
        self.size = 300
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint|Qt.Tool)
        self.resize(self.size, self.size)
        self.selected_vor = 0

        base_path = ruta


        self.fondo = QLabel(self)
        if N == 1:
            self.fondo_pixmap = QPixmap(os.path.join(base_path, "VORBaseN1.png"))
        else:
            self.fondo_pixmap = QPixmap(os.path.join(base_path, "VORBaseN2.png"))
        
        self.fondo_pixmap = self.fondo_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.fondo.setPixmap(self.fondo_pixmap)
        self.fondo.resize(self.size, self.size)


        self.aguja = QLabel(self)

        self.aguja_pixmap = QPixmap(os.path.join(base_path, "VORAguja.png"))
        self.aguja_pixmap = self.aguja_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.aguja.resize(self.size, self.size)
        
        self.angle_indicator = QLabel(self)

        self.angle_indicator_pixmap = QPixmap(os.path.join(base_path, "VORRadiales.png"))
        self.angle_indicator_pixmap = self.angle_indicator_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.angle_indicator.setPixmap(self.angle_indicator_pixmap)
        self.angle_indicator.resize(self.size, self.size)

        self.to_indicator = QLabel(self)

        self.to_indicator_pixmap = QPixmap(os.path.join(base_path, "ToIndicator.png"))
        self.to_indicator_pixmap = self.to_indicator_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.to_indicator.setPixmap(self.to_indicator_pixmap)
        self.to_indicator.resize(self.size, self.size)

        self.from_indicator = QLabel(self)

        self.from_indicator_pixmap = QPixmap(os.path.join(base_path, "FromIndicator.png"))
        self.from_indicator_pixmap = self.from_indicator_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.from_indicator.setPixmap(self.from_indicator_pixmap)
        self.from_indicator.resize(self.size, self.size)
        
        self.vor_selector = QLineEdit("Set_vor",self)
        self.vor_selector.move(20, 130)
        self.vor_selector.setPlaceholderText("Set_Vor")
        self.vor_selector.textChanged.connect(self.set_vor)
        self.vor_selector.setVisible(False)
        self.vor_selector.setEnabled(False)


        self.bus.altitud = 0
        self.actualizar()
        self.bus.updated.connect(self.actualizar)
        self.update_indicator()
    
    def set_vor(self,text):
        if not self.vor_selector.isVisible():
            return
        try:
            self.selected_vor = float(text)
            bus.n1 = float(text)
        except:
            self.selected_vor = 0

    def draw_needle(self, painter, pixmap, angle):
        painter.save()

        pivot_x = self.size / 2
        pivot_y = 70   

        painter.translate(pivot_x, pivot_y)
        painter.rotate(angle)
        painter.translate(-pivot_x, -pivot_y)

        painter.drawPixmap(0, 0, pixmap)

        painter.restore()

    def actualizar(self):
        if not self.isVisible() and self.ready:
            return
        
        def in_cone(point1,point2,angle,opening_angle,distance):
            angle = math.radians(90-float(angle))
            
            opening_angle = math.radians(opening_angle)
            dx = point2[0] - point1[0]
            dy = point2[1] - point1[1]
            dist = math.hypot(dx, dy)
            if dist > distance:
                return False
            angle_to_point = math.atan2(dy, dx)
            diff = math.atan2(math.sin(angle_to_point - angle),math.cos(angle_to_point - angle))
            print(diff)
            return abs(diff) <= opening_angle
        
        def find_neadle_angle(p1,p2,indicator_angle,max_angle):
            dx = p2[0]-p1[0]
            dy = p2[1]-p1[1]
            angle_to_vor = math.degrees(math.atan2(dy, dx)) + 90
            radial = (angle_to_vor + 180) % 360

            error = (radial - indicator_angle + 180) % 360 - 180

            diff = (radial - indicator_angle + 360) % 360

            if diff < 90 or diff > 270:
                
                flag = "FROM"
                self.to_indicator.hide()
                self.from_indicator.show()
            else:
                flag = "TO"
                self.from_indicator.hide()
                self.to_indicator.show()
                if error >0:
                    error = 180 -error
                else:
                    error = -(180+error)
            cdi = max(-max_angle, min(max_angle, error))/max_angle
            return cdi*45

        p1 = [bus.position["x"],bus.position["y"]]
        p2 = [0,0]
        found_vor = False
        for vor in bus.vors:
            if float(vor["freq"]) == self.selected_vor:
                found_vor = vor
                p2 = [vor["x"],vor["y"]]
                break
        needle_angle = 0
        if not found_vor == False and found_vor["typ"] == "VOR":
            needle_angle = find_neadle_angle(p1,p2,self.indicator_angle,10)
        elif not found_vor == False and (found_vor["typ"] == "LOC" or found_vor["typ"] == "ILS"):
            loc_angle = float(found_vor["ang"])
            if in_cone(p2,p1,loc_angle,35,16535) or in_cone(p2,p1,found_vor["ang"],10,23149):
                needle_angle = -find_neadle_angle(p1,p2,loc_angle,2.5)
                self.from_indicator.hide()
                self.to_indicator.show()
            else:
                self.from_indicator.hide()
                self.to_indicator.hide()
        else:
            self.from_indicator.hide()
            self.to_indicator.hide()
            
        final = QPixmap(self.size, self.size)
        final.fill(Qt.transparent)
        painter = QPainter(final)


        painter.drawPixmap(0, 0, self.fondo_pixmap)


        painter.drawPixmap(0, 0, self.angle_indicator.pixmap())


        self.draw_needle(painter, self.aguja_pixmap, needle_angle)

        painter.end()

        self.aguja.setPixmap(final)
    
    def update_indicator(self):

        final = QPixmap(self.size, self.size)
        final.fill(Qt.transparent)

        painter = QPainter(final)


        painter.translate(self.size / 2, self.size / 2)
        painter.rotate(-self.indicator_angle)


        w = self.angle_indicator_pixmap.width()
        h = self.angle_indicator_pixmap.height()

        painter.drawPixmap(int(-w/2), int(-h/2), self.angle_indicator_pixmap)

        painter.end()

        self.angle_indicator.setPixmap(final)

    def modify_angle(self,change_angle):
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.ShiftModifier:
            change_angle *=5
        self.indicator_angle = (self.indicator_angle+change_angle)%360
        self.update_indicator()
        self.actualizar()


    def is_bottom_left(self, x, y):
        w = self.width()
        h = self.height()

        return (
            x < w * 0.15 and    
            y > h * 0.75         
        )
    def is_bottom_left2(self, x, y):

        w = self.width()
        h = self.height()

        return (
            w*0.15 < x < w * 0.3 and     
            y > h * 0.75        
        )
    def is_open_menu(self, x, y):
        w = self.width()
        h = self.height()

        return (
            x < w * 0.2 and     
            y < h * 0.1    
        )

    def mousePressEvent(self, event):
        x = event.x()
        y = event.y()

        
        if Estado.modo_edicion:
            self.offset = event.pos()
        elif self.is_bottom_left(x,y):
            self.modify_angle(-1)
        elif self.is_bottom_left2(x,y):
            self.modify_angle(1)
        elif self.is_open_menu(x,y):
            self.vor_selector.setVisible(not self.vor_selector.isVisible())
            self.vor_selector.setEnabled(self.vor_selector.isVisible())

    def mouseMoveEvent(self, event):
        if Estado.modo_edicion and self.offset:
            self.move(self.pos() + event.pos() - self.offset)



class DME(QWidget):
    def __init__(self, bus):
        super().__init__()
        self.ready = False
        self.bus = bus
        self.offset = None
        self.size = 350
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint|Qt.Tool)
        self.resize(self.size, self.size)
        self.selected = 1
        base_path = ruta
        self.stored_frq = 0

      
        self.fondo = QLabel(self)

        self.fondo_pixmap = QPixmap(os.path.join(base_path, "DMEBase.png"))
        self.fondo_pixmap = self.fondo_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.fondo.setPixmap(self.fondo_pixmap)
        self.fondo.resize(self.size, self.size)
        
        self.aguja_n1 = QLabel(self)

        self.aguja_n1_pixmap = QPixmap(os.path.join(base_path, "DMEAgujaN1.png"))
        self.aguja_n1_pixmap = self.aguja_n1_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.aguja_n1.setPixmap(self.aguja_n1_pixmap)
        self.aguja_n1.resize(self.size, self.size)

        
        self.aguja_n2 = QLabel(self)

        self.aguja_n2_pixmap = QPixmap(os.path.join(base_path, "DMEAgujaN2.png"))
        self.aguja_n2_pixmap = self.aguja_n2_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.aguja_n2.setPixmap(self.aguja_n2_pixmap)
        self.aguja_n2.resize(self.size, self.size)
        self.aguja_n2.hide()


        self.aguja_n3 = QLabel(self)

        self.aguja_n3_pixmap = QPixmap(os.path.join(base_path, "DMEAgujaN3.png"))
        self.aguja_n3_pixmap = self.aguja_n3_pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.aguja_n3.setPixmap(self.aguja_n3_pixmap)
        self.aguja_n3.resize(self.size, self.size)
        self.aguja_n3.hide()

        self.frq_selector = QLineEdit("",self)
        self.frq_selector.move(229, 192)
        self.frq_selector.setPlaceholderText("set_freq")
        self.frq_selector.textChanged.connect(self.set_stored_freq)
        self.frq_selector.setVisible(False)
        self.frq_selector.setEnabled(False)
        self.frq_selector.setFixedWidth(60)
        regex = QRegExp(r"^\d{1,3}(\.\d{1,2})?$")
        validator = QRegExpValidator(regex)

        self.frq_selector.setValidator(validator)

        

   


      
        self.actualizar()
        self.bus.updated.connect(self.actualizar)
        
    def set_stored_freq(self,text):
        self.stored_frq = float(text)

    def actualizar(self):
        pixmap = self.fondo_pixmap.copy()
        painter = QPainter(pixmap)
        painter.setPen(QColor(156, 7, 2))  
        painter.scale(1.5, 1.5)

        distance = "000.0"
        ground_speed = "000"
        time = "000"
        frequency = "000.00"

        if self.selected == 1:
            frequency = bus.n1
        elif self.selected == 2:
            frequency = bus.n2
        elif self.selected == 3:
            frequency = self.stored_frq

        station = False
        for new_station in bus.vors:
            if float(new_station["freq"]) == frequency:
                station = new_station
                break

        frequency = float(math.trunc(frequency*100)/100)
        frequency = f"{frequency:06.2f}"
        
        if not station == False and station.get("DME") == True:
            distance = math.sqrt((bus.position["x"]-station["x"])**2+(bus.position["y"]-station["y"])**2)
            distance = math.sqrt(distance**2+(bus.altitud*1.8372)**2)
            ground_speed = bus.ground_speed
            if ground_speed == 0:
                time = 0
            else:     
                time = (0.5442765*distance)/ground_speed
            distance =distance/3307.14286

            distance = float(math.trunc(distance*10)/10)
            distance = f"{distance:05.1f}"
            ground_speed = int(math.trunc(ground_speed))
            ground_speed = f"{ground_speed:03d}"
            time = int(math.trunc(time/60))
            time = f"{time:03d}"




        painter.drawText(40, 44, distance)  
        painter.drawText(110, 44, ground_speed)
        painter.drawText(163, 44, time)
        painter.drawText(152,78,frequency)
        painter.end()
        self.fondo.setPixmap(pixmap)

    def tune_dme(self,seting):
        self.aguja_n1.hide()
        self.aguja_n2.hide()
        self.aguja_n3.hide()
        print(seting)
        self.selected = seting
        if seting == 1:
            self.aguja_n1.show()
        elif seting == 2:
            self.aguja_n2.show()
        elif seting == 3:
            self.aguja_n3.show()
            

    def is_n1(self, x, y):
        w = self.width()
        h = self.height()

        return (
            138 < x < 155 and     
            190< y <210       
        )
    def is_n2(self, x, y):
        w = self.width()
        h = self.height()

        return (
            165 <x < 183 and    
            177<y<187        
        )
    def is_n3(self, x, y):
        w = self.width()
        h = self.height()

        return (
            196<x < 219 and     
            190< y < 210        
        )
    def is_set_freq(self, x, y):
        w = self.width()
        h = self.height()

        return (
            292<x < 303 and    
            190< y < 200       
        )

    def mousePressEvent(self, event):
        x = event.x()
        y = event.y()
        if Estado.modo_edicion:
            self.offset = event.pos()
        elif self.is_n1(x,y):
            self.tune_dme(1)
        elif self.is_n2(x,y):
            self.tune_dme(2)
        elif self.is_n3(x,y):
            self.tune_dme(3)
        elif self.is_set_freq(x,y):
            self.frq_selector.setVisible(not self.frq_selector.isVisible())
            self.frq_selector.setEnabled(self.frq_selector.isVisible())
        

    def mouseMoveEvent(self, event):
        if Estado.modo_edicion and self.offset:
            self.move(self.pos() + event.pos() - self.offset)



class Map(QWidget):
    def __init__(self):
        super().__init__()

        self.setFixedSize(1100, 850)

        base_path = ruta

      
        self.original_pixmap = QPixmap(
            os.path.join(base_path, "EnrouteMap.png")
        )

        self.label = QLabel(self)
        self.label.setGeometry(self.rect())

        self.lines = []
        self.temp_start = None
        self.temp_end = None
        self.drawing = False

        self.setMouseTracking(True)

        self.update_map()

   
    def resizeEvent(self, event):
        self.label.setGeometry(self.rect())
        self.update_map()

    def update_map(self):
        self.scaled_pixmap = self.original_pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.scale = self.scaled_pixmap.width() / self.original_pixmap.width()
        self.render()

   
    def world_to_screen(self, x, y):
        sx = x * self.scale
        sy = (self.original_pixmap.height() - y) * self.scale
        return sx, sy

    def screen_to_world(self, x, y):
        wx = x / self.scale
        wy = self.original_pixmap.height() - (y / self.scale)
        return wx, wy

   
    def bearing(self, p1, p2):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        dy = -dy
        dx = -dx

        angle = math.degrees(math.atan2(dx, dy))
        return angle % 360

    def opposite_angle(self, angle):
        return (angle + 180) % 360

    def midpoint(self, p1, p2):
        return (
            (p1[0] + p2[0]) / 2,
            (p1[1] + p2[1]) / 2
        )

    
    def add_line(self, p1, p2):
        self.lines.append({
            "p1": p1,
            "p2": p2
        })

   
    def remove_near(self, x, y, radius=12):
        new = []

        for l in self.lines:
            p1 = self.world_to_screen(*l["p1"])
            p2 = self.world_to_screen(*l["p2"])

            if self.point_to_segment_distance(
                x, y,
                p1[0], p1[1],
                p2[0], p2[1]
            ) > radius:
                new.append(l)

        self.lines = new
        self.render()

   
    def point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)

        t = ((px - x1)*dx + (py - y1)*dy) / (dx*dx + dy*dy)
        t = max(0, min(1, t))

        cx = x1 + t * dx
        cy = y1 + t * dy

        return math.hypot(px - cx, py - cy)

   
    def mousePressEvent(self, event):
        ctrl = event.modifiers() & Qt.ControlModifier

        if ctrl:
            self.remove_near(event.x(), event.y())
            return

        self.temp_start = self.screen_to_world(event.x(), event.y())
        self.temp_end = self.temp_start
        self.drawing = True

   
    def mouseMoveEvent(self, event):
        if self.drawing and self.temp_start is not None:
            self.temp_end = self.screen_to_world(event.x(), event.y())
            self.render()

   
    def mouseReleaseEvent(self, event):
        if not self.drawing or self.temp_start is None:
            return

        end = self.screen_to_world(event.x(), event.y())

        self.add_line(self.temp_start, end)

        self.temp_start = None
        self.temp_end = None
        self.drawing = False

        self.render()

    
    def render(self):
        final = QPixmap(self.size())
        final.fill(Qt.transparent)

        painter = QPainter(final)


        painter.drawPixmap(0, 0, self.scaled_pixmap)

        for line in self.lines:
            p1 = self.world_to_screen(*line["p1"])
            p2 = self.world_to_screen(*line["p2"])


            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))


            angle = self.bearing(line["p1"], line["p2"])
            angle2 = self.opposite_angle(angle)

            mx, my = self.midpoint(p1, p2)

            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.drawText(int(mx), int(my), f"{angle:.0f}° / {angle2:.0f}°")


        if self.drawing and self.temp_start and self.temp_end:
            p1 = self.world_to_screen(*self.temp_start)
            p2 = self.world_to_screen(*self.temp_end)


            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))


            angle = self.bearing(self.temp_start, self.temp_end)
            angle2 = self.opposite_angle(angle)

            mx, my = self.midpoint(p1, p2)

            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.drawText(int(mx), int(my), f"{angle:.0f}° / {angle2:.0f}°")

        painter.end()

        self.label.setPixmap(final)

class Menu(QWidget):
    def __init__(self, altimetro):
        super().__init__()

        self.altimetro = altimetro
        self.VIS = VerticalSpeedIndicatior(bus)
        self.vor1 = Vor_1(bus,1)
        self.vor2 = Vor_1(bus,2)
        self.dme = DME(bus)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.resize(250, 170)

        self.label = QLabel("MENU", self)
        self.label.move(112, 10)

        self.btn_alt = QPushButton("Altímetro ON/OFF", self)
        self.btn_alt.move(10, 50)
        self.btn_alt.clicked.connect(self.toggle_alt)

        self.btn_vis = QPushButton("VIS ON/OFF", self)
        self.btn_vis.move(130, 50)
        self.btn_vis.clicked.connect(self.toggle_vis)

        self.Vbtn_vor1 = QPushButton("VOR1 ON/OFF", self)
        self.Vbtn_vor1.move(10, 80)
        self.Vbtn_vor1.clicked.connect(self.toggle_vor1)

        self.Vbtn_vor2 = QPushButton("VOR2 ON/OFF", self)
        self.Vbtn_vor2.move(130, 80)
        self.Vbtn_vor2.clicked.connect(self.toggle_vor2)

        self.btn_dme = QPushButton("DME ON/OFF", self)
        self.btn_dme.move(10,110)
        self.btn_dme.clicked.connect(self.toggle_dme)

        self.btn_close = QPushButton("Cerrar", self)
        self.btn_close.move(160, 140)
        self.btn_close.clicked.connect(QApplication.quit)
        self.btn_close.setFixedWidth(70)

        self.player_text = QLineEdit("",self)
        self.player_text.move(10, 140)
        self.player_text.setPlaceholderText("PlayerName")
        self.player_text.textChanged.connect(self.set_player)

    def toggle_alt(self):
        self.altimetro.setVisible(not self.altimetro.isVisible())

    def toggle_vis(self):
        self.VIS.setVisible(not self.VIS.isVisible())

    def toggle_vor1(self):
        self.vor1.setVisible(not self.vor1.isVisible())

    def toggle_vor2(self):
        self.vor2.setVisible(not self.vor2.isVisible())

    def toggle_dme(self):
        self.dme.setVisible(not self.dme.isVisible())

    def set_player(self,text):
        bus.set_player(text)


class Cockpit:
    def __init__(self, app):

        self.app = app

        self.altimetro = Altimetro(bus)
        self.menu = Menu(self.altimetro)

        self.altimetro.move(300, 200)
        self.altimetro.move(300, 400)
        self.menu.move(50, 50)

        self.menu.show()

        self.map = Map()
        self.map.move(200, 200)
        self.map.show()
        self.map.setVisible(False)
        
        keyboard.add_hotkey("ctrl+m", self.toggle)
        keyboard.add_hotkey("ctrl+b", self.toggle_map)

    def toggle(self):
        Estado.modo_edicion = not Estado.modo_edicion

        self.menu.setVisible(not self.menu.isVisible())

        if self.menu.isVisible():
            self.menu.raise_()
    def toggle_map(self):
        self.map.setVisible(not self.map.isVisible())




app = QApplication(sys.argv)

cockpit = Cockpit(app)

sys.exit(app.exec_())