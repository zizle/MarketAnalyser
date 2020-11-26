# _*_ coding:utf-8 _*_
# @File  : web.py
# @Time  : 2020-11-26 15:38
# @Author: zizle
from PyQt5.QtCore import Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QEventLoop
from PyQt5.QtWebChannel import QWebChannel


class WebChartWidget(QWebEngineView):
    def __init__(self, web_channel, file_url, *args, **kwargs):
        super(WebChartWidget, self).__init__(*args, **kwargs)
        # 加载图形容器
        self.load(QUrl(file_url))  # 加载页面
        # 设置与页面信息交互的通道
        channel_qt_obj = QWebChannel(self.page())  # 实例化qt信道对象,必须传入页面参数
        self.contact_channel = web_channel  # 页面信息交互通道
        self.page().setWebChannel(channel_qt_obj)
        channel_qt_obj.registerObject("pageContactChannel", self.contact_channel)  # 信道对象注册信道，只能注册一个
        event_loop = QEventLoop(self)  # 加载页面同步
        self.loadFinished.connect(event_loop.quit)
        event_loop.exec_()

    def resizeEvent(self, event):
        super(WebChartWidget, self).resizeEvent(event)
        # 重新设置图形的高度
        self.contact_channel.chartResize.emit(self.width() * 0.8, self.height())