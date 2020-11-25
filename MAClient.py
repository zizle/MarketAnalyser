# _*_ coding:utf-8 _*_
# @File  : MAClient.py
# @Time  : 2020-11-25 16:00
# @Author: zizle
""" 主入口 """
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from windows.principal import MainWindow

app = QApplication(sys.argv)
font = QFont()
font.setPointSize(11)
font.setStyleStrategy(QFont.PreferAntialias)
app.setFont(font)
main_app = MainWindow()
main_app.show()
sys.exit(app.exec_())
