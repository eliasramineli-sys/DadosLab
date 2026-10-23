"""Perspective cube with depth-sorted faces and projected pips; no GPU required."""
import math
import time
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPolygonF, QLinearGradient, QRadialGradient, QPen
from PySide6.QtWidgets import QWidget


PIPS = {
    1: [(0,0)], 2: [(-1,-1),(1,1)], 3: [(-1,-1),(0,0),(1,1)],
    4: [(-1,-1),(-1,1),(1,-1),(1,1)],
    5: [(-1,-1),(-1,1),(0,0),(1,-1),(1,1)],
    6: [(-1,-1),(-1,0),(-1,1),(1,-1),(1,0),(1,1)]}
# Opposite sides sum to seven. Each local plane carries a face number.
FACES = [(1,[0,0,1],[1,0,0],[0,1,0]), (6,[0,0,-1],[-1,0,0],[0,1,0]),
    (2,[1,0,0],[0,0,-1],[0,1,0]), (5,[-1,0,0],[0,0,1],[0,1,0]),
    (3,[0,1,0],[1,0,0],[0,0,-1]), (4,[0,-1,0],[1,0,0],[0,0,1])]
NORMALS = {face: np.asarray(normal, float) for face,normal,_,_ in FACES}


def rotation(x, y, z):
    cx,sx,cy,sy,cz,sz = math.cos(x),math.sin(x),math.cos(y),math.sin(y),math.cos(z),math.sin(z)
    return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]]) @ np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]) @ np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])


def face_orientation(face):
    # Map the chosen outward normal to the front (+Z), then tilt for a three-face view.
    angles = {1:(0,0,0),6:(0,math.pi,0),2:(0,-math.pi/2,0),
        5:(0,math.pi/2,0),3:(math.pi/2,0,0),4:(-math.pi/2,0,0)}
    return rotation(.30,.38,-.09) @ rotation(*angles[face])


class DieWidget(QWidget):
    landed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.setAccessibleName("Dado virtual tridimensional")
        self.face = 1
        self.running = False
        self.started = 0
        self.duration = 1.35
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.tick)

    def roll(self, face, animate=True):
        self.face = face
        self.setAccessibleDescription(f"Face sorteada: {face}")
        if not animate:
            self.update()
            self.landed.emit(face)
            return
        self.started = time.monotonic()
        self.running = True
        self.timer.start()
        self.update()

    def tick(self):
        if time.monotonic() - self.started >= self.duration:
            self.running = False
            self.timer.stop()
            self.update()
            self.landed.emit(self.face)
        else:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width,height = self.width(), self.height()
        t = min(1, (time.monotonic()-self.started)/self.duration) if self.running else 1
        rest = face_orientation(self.face)
        remaining = (1-t)**2
        matrix = rotation(remaining*math.pi*5, remaining*math.pi*7, remaining*math.pi*3) @ rest
        jump = abs(math.sin(t*math.pi*3)) * (1-t) * 72 if self.running else 0
        horizontal = math.sin(t*math.pi*2)*(1-t)*30 if self.running else 0
        cx,cy = width/2+horizontal, height*.46-jump
        scale = min(width,height)*.265
        shadow = QRadialGradient(QPointF(width/2,height*.80),width*.35)
        shadow.setColorAt(0,QColor(3,7,18,160))
        shadow.setColorAt(1,QColor(3,7,18,0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow)
        painter.drawEllipse(QRectF(width*.13,height*.71,width*.74,height*.18))

        def project(point):
            v = matrix @ point
            factor = 5.5 / (5.5-v[2])
            return QPointF(cx+v[0]*scale*factor,cy-v[1]*scale*factor)

        planes=[]
        camera=np.array([0,0,5.5])
        for face,normal,u,v in FACES:
            normal,u,v=map(lambda p:np.asarray(p,float),(normal,u,v))
            transformed=matrix@normal
            if np.dot(transformed,camera-transformed) <= 0:
                continue
            planes.append((transformed[2],face,normal,u,v))
        for _,face,normal,u,v in sorted(planes,key=lambda item:item[0]):
            corners = QPolygonF([project(normal + a*u + b*v) for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]])
            brightness = .73 + .22 * max(0,(matrix@normal)[2])
            gradient=QLinearGradient(corners[0],corners[2])
            gradient.setColorAt(0,QColor.fromRgbF(brightness, min(1,brightness+.03),min(1,brightness+.07)))
            gradient.setColorAt(1,QColor.fromRgbF(brightness*.80,brightness*.84,brightness*.92))
            painter.setPen(QPen(QColor("#aebed5"),1.2))
            painter.setBrush(gradient)
            painter.drawPolygon(corners)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#182945"))
            for a,b in PIPS[face]:
                center=normal*1.002+u*a*.51+v*b*.51
                ring=QPolygonF([project(center + .135*(math.cos(angle)*u+math.sin(angle)*v)) for angle in np.linspace(0,2*math.pi,25)])
                painter.drawPolygon(ring)
