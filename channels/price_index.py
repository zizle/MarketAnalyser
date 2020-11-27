# _*_ coding:utf-8 _*_
# @File  : price_index.py
# @Time  : 2020-11-26 15:30
# @Author: zizle
""" 价格指数的界面交互信息通道 """
from PyQt5.QtCore import QObject, pyqtSignal


# 指数信道
class PriceIndexChannel(QObject):
    # 参数1：作图的源数据; 参数2: 基本配置信息
    lineData = pyqtSignal(str, str)   # 普通数据
    seasonData = pyqtSignal()  # 季节数据
    # 参数1: 图形宽度; 参数2: 图形高度
    chartResize = pyqtSignal(int, int)


