# _*_ coding:utf-8 _*_
# @File  : price_index.py
# @Time  : 2020-11-25 16:01
# @Author: zizle
""" 价格指数窗口 """
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel


class PriceIndexWin(QWidget):
    """ 价格净持仓窗口 """
    def __init__(self, *args, **kwargs):
        super(PriceIndexWin, self).__init__(*args, **kwargs)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("价格指数窗口"))
        self.setLayout(layout)