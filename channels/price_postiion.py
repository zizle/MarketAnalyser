# _*_ coding:utf-8 _*_
# @File  : price_postiion.py
# @Time  : 2020-11-26 10:44
# @Author: zizle
from PyQt5.QtCore import QObject, pyqtSignal


class ChartSourceChannel(QObject):
    # 参数1：作图的源数据; 参数2: 基本配置信息
    chartSource = pyqtSignal(str, str)
    # 参数1: 图形宽度; 参数2: 图形高度
    chartResize = pyqtSignal(int, int)