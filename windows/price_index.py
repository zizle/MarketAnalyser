# _*_ coding:utf-8 _*_
# @File  : price_index.py
# @Time  : 2020-11-25 16:01
# @Author: zizle
""" 价格指数窗口 """
import json
from PyQt5.QtWidgets import (qApp, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton,
                             QSplitter, QTableWidget, QHeaderView)
from PyQt5.QtCore import Qt, QMargins, QUrl
from PyQt5.QtNetwork import QNetworkRequest
from widgets import TitleOptionWidget, WebChartWidget
from channels.price_index import PriceIndexChannel
from settings import EXCHANGES, SERVER_API
from utils.logger import logger


class ChartContainWidget(WebChartWidget):
    def set_chart_option(self, source_data, base_option):
        """ 传入数据设置图形 """
        self.contact_channel.lineData.emit(source_data, base_option)
        self.contact_channel.chartResize.emit(self.width() * 0.8, self.height())


class PriceIndexWin(QWidget):
    """ 价格净持仓窗口 """
    def __init__(self, *args, **kwargs):
        super(PriceIndexWin, self).__init__(*args, **kwargs)
        layout = QVBoxLayout()
        layout.setContentsMargins(QMargins(0, 0, 0, 0))
        # 操作头
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignLeft)
        title_layout.addWidget(QLabel("交易所:", self))
        self.exchange_combobox = QComboBox(self)
        title_layout.addWidget(self.exchange_combobox)
        title_layout.addWidget(QLabel("期货品种:", self))
        self.variety_combobox = QComboBox(self)
        self.variety_combobox.setMinimumWidth(100)
        title_layout.addWidget(self.variety_combobox)
        title_layout.addWidget(QLabel("起始日期:"))
        self.start_date = QDateEdit(self)
        self.start_date.setDisplayFormat('yyyy-MM-dd')
        self.start_date.setCalendarPopup(True)
        title_layout.addWidget(self.start_date)
        title_layout.addWidget(QLabel("终止日期:"))
        self.end_date = QDateEdit(self)
        self.end_date.setDisplayFormat('yyyy-MM-dd')
        self.end_date.setCalendarPopup(True)
        title_layout.addWidget(self.end_date)

        self.analysis_button = QPushButton("开始分析", self)
        title_layout.addWidget(self.analysis_button)
        # 查看涨跌
        self.up_down_button = QPushButton('季节图表', self)
        self.up_down_button.setEnabled(False)
        title_layout.addWidget(self.up_down_button)

        self.option_widget = TitleOptionWidget(self)
        self.option_widget.setLayout(title_layout)
        layout.addWidget(self.option_widget)

        # 图形表格拖动区
        splitter = QSplitter(Qt.Vertical, self)
        splitter.setContentsMargins(QMargins(10, 5, 10, 5))
        # 图形区
        self.chart_container = ChartContainWidget(PriceIndexChannel(), 'file:///templates/price_position.html', self)
        splitter.addWidget(self.chart_container)
        # 表格区
        self.data_table = QTableWidget(self)
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(['日期', '价格指数', '总持仓', '总成交量'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.data_table)
        splitter.setSizes([self.parent().height() * 0.6, self.parent().height() * 0.4])
        layout.addWidget(splitter)
        self.setLayout(layout)

        """ 逻辑业务部分 """
        self.network_manager = getattr(qApp, 'network')
        # 关联交易所改变信号
        self.exchange_combobox.currentTextChanged.connect(self.get_variety_with_exchange)
        # 添加交易所
        for exchange_item in EXCHANGES:
            self.exchange_combobox.addItem(exchange_item['name'], exchange_item['id'])

    def get_variety_with_exchange(self):
        """ 获取交易所下的所有品种 """
        url = SERVER_API + 'exchange-variety/?is_real=1&exchange={}'.format(self.exchange_combobox.currentData())
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.exchange_variety_reply)

    def exchange_variety_reply(self):
        # 交易所品种返回
        reply = self.sender()
        if reply.error():
            logger.error('GET EXCHANGE VARIETY ERROR. STATUS:{}'.format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            self.set_current_variety(data['varieties'])
        reply.deleteLater()

    def set_current_variety(self, varieties: list):
        """ 设置当前的品种 """
        self.variety_combobox.clear()
        for variety_item in varieties:
            self.variety_combobox.addItem(variety_item['variety_name'], variety_item['variety_en'])


# 权重指数窗口
class WeightPriceWin(PriceIndexWin):
    pass


# 主力指数窗口
class DominantPriceWin(PriceIndexWin):
    pass
