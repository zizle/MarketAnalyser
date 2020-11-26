# _*_ coding:utf-8 _*_
# @File  : title.py
# @Time  : 2020-11-26 15:22
# @Author: zizle
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class TitleOptionWidget(QWidget):
    """ 操作标题栏 """
    def __init__(self, *args, **kwargs):
        super(TitleOptionWidget, self).__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_StyledBackground, True)  # 必须设置,如果不设置将导致子控件产生阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(100, 100, 100))
        shadow.setBlurRadius(5)
        self.setGraphicsEffect(shadow)
        self.setObjectName("optionWidget")
        self.setStyleSheet("#optionWidget{background-color:rgb(245,245,245)}")