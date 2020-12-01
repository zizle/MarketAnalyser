# _*_ coding:utf-8 _*_
# @File  : constant.py
# @Time  : 2020-11-30 08:42
# @Author: zizle
""" 常量 """

HORIZONTAL_SCROLL_STYLE = "QScrollBar:horizontal{background:transparent;height:10px;margin:0px;}" \
            "QScrollBar:horizontal:hover{background:rgba(0,0,0,30);border-radius:5px}" \
            "QScrollBar::handle:horizontal{background:rgba(0,0,0,50);height:10px;border-radius:5px;border:none}" \
            "QScrollBar::handle:horizontal:hover{background:rgba(0,0,0,100)}" \
            "QScrollBar::add-page:horizontal{height:10px;background:transparent;}" \
            "QScrollBar::sub-page:horizontal{height:10px;background:transparent;}" \
            "QScrollBar::sub-line:horizontal{width:0px}" \
            "QScrollBar::add-line:horizontal{width:0px}"

VERTICAL_SCROLL_STYLE = "QScrollBar:vertical{background: transparent; width:10px;margin: 0px;}" \
            "QScrollBar:vertical:hover{background:rgba(0,0,0,30);border-radius:5px}" \
            "QScrollBar::handle:vertical{background:rgba(0,0,0,50);min-height:30px;border-radius:5px}" \
            "QScrollBar::handle:vertical:hover{background:rgba(0,0,0,100);min-height:30px}" \
            "QScrollBar::add-page:vertical{width:10px;background:transparent;}" \
            "QScrollBar::sub-page:vertical{width:10px;background:transparent;}" \
            "QScrollBar::sub-line:vertical{height:0px}" \
            "QScrollBar::add-line:vertical{height:0px}"

HORIZONTAL_HEADER_STYLE = "QHeaderView::section{background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1," \
            "stop:0 #49aa54, stop: 0.48 #49cc54,stop: 0.52 #49cc54, stop:1 #49aa54);" \
            "border:1px solid rgb(201,202,202);border-left:none;" \
            "min-height:25px;min-width:40px;font-weight:bold;font-size:13px};"