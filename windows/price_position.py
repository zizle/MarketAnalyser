# _*_ coding:utf-8 _*_
# @File  : price_position.py
# @Time  : 2020-11-25 16:00
# @Author: zizle
""" 价格 - 净持仓窗口 """

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel


class PricePositionWin(QWidget):
    """ 价格净持仓窗口 """
    def __init__(self, *args, **kwargs):
        super(PricePositionWin, self).__init__(*args, **kwargs)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("11111111窗口"))
        self.setLayout(layout)