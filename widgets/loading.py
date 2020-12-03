# _*_ coding:utf-8 _*_
# @File  : loading.py
# @Time  : 2020-11-30 14:43
# @Author: zizle

from PyQt5.QtCore import QSize, pyqtProperty, QTimer, Qt, QMargins, QRect
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QWidget, QLabel, QDialog, QVBoxLayout, QGraphicsOpacityEffect


class CircleProgressBar(QWidget):
    Color = QColor(24, 189, 155)  # 圆圈颜色
    Clockwise = True  # 顺时针还是逆时针
    Delta = 36

    def __init__(self, *args, color=None, clockwise=True, **kwargs):
        super(CircleProgressBar, self).__init__(*args, **kwargs)
        self.angle = 0
        self.Clockwise = clockwise
        if color:
            self.Color = color
        self._timer = QTimer(self, timeout=self.update)
        self._timer.start(100)
        self.setFixedSize(70,70)

    def paintEvent(self, event):
        super(CircleProgressBar, self).paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        side = min(self.width(), self.height())
        painter.scale(side / 100.0, side / 100.0)
        painter.rotate(self.angle)
        painter.save()
        painter.setPen(Qt.NoPen)
        color = self.Color.toRgb()
        for i in range(11):
            color.setAlphaF(1.0 * i / 10)
            painter.setBrush(color)
            painter.drawEllipse(30, -10, 20, 20)
            painter.rotate(36)
        painter.restore()
        self.angle += self.Delta if self.Clockwise else -self.Delta
        self.angle %= 360

    @pyqtProperty(QColor)
    def color(self) -> QColor:
        return self.Color

    @color.setter
    def color(self, color: QColor):
        if self.Color != color:
            self.Color = color
            self.update()

    @pyqtProperty(bool)
    def clockwise(self) -> bool:
        return self.Clockwise

    @clockwise.setter
    def clockwise(self, clockwise: bool):
        if self.Clockwise != clockwise:
            self.Clockwise = clockwise
            self.update()

    @pyqtProperty(int)
    def delta(self) -> int:
        return self.Delta

    @delta.setter
    def delta(self, delta: int):
        if self.delta != delta:
            self.delta = delta
            self.update()

    def sizeHint(self) -> QSize:
        return QSize(100, 100)


class LoadingWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super(LoadingWidget, self).__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout()
        layout.setContentsMargins(QMargins(0, 15, 0, 15))
        c = CircleProgressBar(self)
        c.setFixedSize(30, 30)
        layout.addWidget(c, alignment=Qt.AlignHCenter)
        self.tip_label = QLabel('请求数据中', self)
        layout.addWidget(self.tip_label, alignment=Qt.AlignHCenter)

        self.setFixedSize(240, 80)
        # 透明度
        opacity_effect = QGraphicsOpacityEffect(self)
        opacity_effect.setOpacity(0.8)
        self.setGraphicsEffect(opacity_effect)

        self.setLayout(layout)

    def paintEvent(self, event):
        # 画2个表框
        super(LoadingWidget, self).paintEvent(event)
        painter = QPainter(self)
        # painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(20, 20, 20), 2))
        painter.drawRect(self.rect())

        painter.setPen(QPen(QColor(30, 30, 30), 1))
        inner_rect = QRect(8, 8, self.rect().width() - 16, self.rect().height() - 16)
        painter.drawRect(inner_rect)


class LoadingCover(QWidget):
    def __init__(self, *args, **kwargs):
        super(LoadingCover, self).__init__(*args, **kwargs)
        # self.setAttribute(Qt.WA_StyledBackground, True)   # 有背景色
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(QMargins(0, 0, 0, 0))
        self.tip_show = LoadingWidget(self)



        main_layout.addWidget(self.tip_show, alignment=Qt.AlignCenter)
        self.setLayout(main_layout)

        self.tip_show.setObjectName('tipShow')
        self.setObjectName('loadingCover')
        self.setStyleSheet(
            "#loadingCover{background-color:rgb(160,160,160)}"
            "#tipShow{background-color:rgb(160,160,160)}"
        )

    def show(self, text: str = '请求数据中'):
        super(LoadingCover, self).show()
        self.tip_show.tip_label.setText(text)