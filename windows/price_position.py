# _*_ coding:utf-8 _*_
# @File  : price_position.py
# @Time  : 2020-11-25 16:00
# @Author: zizle
""" 价格 - 净持仓窗口 """
import json
import datetime
from PyQt5.QtWidgets import (qApp, QWidget, QHBoxLayout, QVBoxLayout, QTableWidgetItem, QLabel,
                             QSplitter, QTableWidget, QComboBox, QDateEdit, QPushButton, QHeaderView, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QMargins, QUrl, QDate, QEventLoop
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtWebChannel import QWebChannel
from utils.logger import logger
from channels.price_postiion import ChartSourceChannel
from widgets import TitleOptionWidget, WebChartWidget
from settings import EXCHANGES, SERVER_API


class ChartContainWidget(WebChartWidget):
    def set_chart_option(self, source_data, base_option):
        """ 传入数据设置图形 """
        self.contact_channel.chartSource.emit(source_data, base_option)
        self.contact_channel.chartResize.emit(self.width() * 0.8, self.height())


class PricePositionWin(QWidget):
    """ 价格净持仓窗口 """
    def __init__(self, *args, **kwargs):
        super(PricePositionWin, self).__init__(*args, **kwargs)
        """ UI部分 """
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
        title_layout.addWidget(QLabel("合约:", self))
        self.contract_combobox = QComboBox(self)
        title_layout.addWidget(self.contract_combobox)
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
        self.option_widget = TitleOptionWidget(self)
        self.option_widget.setLayout(title_layout)
        layout.addWidget(self.option_widget)

        # 图形表格拖动区
        splitter = QSplitter(Qt.Vertical, self)
        splitter.setContentsMargins(QMargins(10, 5, 10, 5))
        # 图形区
        self.chart_container = ChartContainWidget(ChartSourceChannel(), 'file:///templates/price_position.html', self)
        splitter.addWidget(self.chart_container)
        # 表格区
        self.data_table = QTableWidget(self)
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(['日期', '收盘价', '总持仓', '多头', '空头', '净持仓', '净持仓率'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.addWidget(self.data_table)
        splitter.setSizes([self.parent().height() * 0.6, self.parent().height() * 0.4])
        layout.addWidget(splitter)

        self.setLayout(layout)

        """ 业务逻辑部分 """

        # 网管器
        self.network_manager = getattr(qApp, 'network')
        # 关联交易所变化信号
        self.exchange_combobox.currentTextChanged.connect(self.get_variety_with_exchange)
        # 关联品种变化信号
        self.variety_combobox.currentTextChanged.connect(self.get_contract_with_variety)
        # 关联合约变化的信号
        self.contract_combobox.currentTextChanged.connect(self.get_min_max_date_with_contract)
        # 添加交易所
        for exchange_item in EXCHANGES:
            self.exchange_combobox.addItem(exchange_item['name'], exchange_item['id'])
        # 关联开始计算按钮信号
        self.analysis_button.clicked.connect(self.get_analysis_data)

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

    def get_contract_with_variety(self):
        """ 根据品种获取全部合约 """
        if not self.variety_combobox.currentData():
            return
        url = SERVER_API + 'price-position-contracts/?variety_en={}'.format(self.variety_combobox.currentData())
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.variety_contracts_reply)

    def variety_contracts_reply(self):
        """ 品种的所有合约返回 """
        reply = self.sender()
        if reply.error():
            logger.error("GET CONTRACTS OF VARIETY ERROR. STATUS:{}".format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            self.set_current_contract(data['contracts'])
        reply.deleteLater()

    def set_current_contract(self, contracts: list):
        self.contract_combobox.clear()
        for contract_item in contracts:
            self.contract_combobox.addItem(contract_item['contract'])

    def get_min_max_date_with_contract(self):
        """ 根据合约获取时间范围 """
        if not self.contract_combobox.currentText():
            return
        url = SERVER_API + 'price-position-dates/?contract={}'.format(self.contract_combobox.currentText())
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.min_max_date_reply)

    def min_max_date_reply(self):
        """ 日期值返回 """
        reply = self.sender()
        if reply.error():
            logger.error("GET MIN & MAX DATE WITH CONTRACT ERROR. STATUS:{}".format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            min_max_date = data["dates"]
            self.set_min_and_max_date(min_max_date['min_date'], min_max_date['max_date'])
        reply.deleteLater()

    def set_min_and_max_date(self, min_date: int, max_date: int):
        """ 设置最大最小日期 """
        if not min_date or not max_date:
            self.analysis_button.setEnabled(False)
            return
        min_date = datetime.datetime.fromtimestamp(min_date)
        max_date = datetime.datetime.fromtimestamp(max_date)
        q_min_date = QDate(min_date.year, min_date.month, min_date.day)
        q_max_date = QDate(max_date.year, max_date.month, max_date.day)
        self.start_date.setDateRange(q_min_date, q_max_date)
        self.start_date.setDate(q_min_date)
        self.end_date.setDateRange(q_min_date, q_max_date)
        self.end_date.setDate(q_max_date)
        self.analysis_button.setEnabled(True)

    def get_analysis_data(self):
        """ 获取结果数据 """
        if not self.contract_combobox.currentText():
            QMessageBox.information(self, '错误', '请先选择合约后再操作.')
            return
        min_date = int(datetime.datetime.strptime(self.start_date.text(), '%Y-%m-%d').timestamp())
        max_date = int(datetime.datetime.strptime(self.end_date.text(), '%Y-%m-%d').timestamp())
        url = SERVER_API + 'price-position/?contract={}&min_date={}&max_date={}'.format(
            self.contract_combobox.currentText(), min_date, max_date
        )
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.price_position_reply)

    def price_position_reply(self):
        """ 获取数据返回 """
        reply = self.sender()
        if reply.error():
            logger.error("GET PRICE-POSITION DATA ERROR. STATUS:{}".format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            self.set_current_data_to_table(data['data'].copy())  # 数据在表格展示
            # 组合基本配置信息和源数据传递到页面
            base_option = {
                'title': '{}价格与净持率趋势图'.format(self.contract_combobox.currentText())
            }
            self.set_current_chart_to_page(json.dumps(data['data']), json.dumps(base_option))
        reply.deleteLater()

    def set_current_data_to_table(self, data_items: list):
        """ 将数据在表格显示 """
        self.data_table.clearContents()
        self.data_table.setRowCount(len(data_items))
        data_items.reverse()
        for row, row_item in enumerate(data_items):
            t_item0 = QTableWidgetItem(row_item['date'])
            t_item0.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 0, t_item0)
            t_item1 = QTableWidgetItem(str(row_item['close_price']))
            t_item1.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 1, t_item1)
            t_item2 = QTableWidgetItem(str(row_item['empty_volume']))
            t_item2.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 2, t_item2)
            t_item3 = QTableWidgetItem(str(row_item['long_position']))
            t_item3.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 3, t_item3)
            t_item4 = QTableWidgetItem(str(row_item['short_position']))
            t_item4.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 4, t_item4)
            t_item5 = QTableWidgetItem(str(row_item['long_position'] - row_item['short_position']))
            t_item5.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 5, t_item5)
            rate = '-' if row_item['empty_volume'] == 0 else str(round((row_item['long_position'] - row_item['short_position']) * 100/row_item['empty_volume'], 2))
            t_item6 = QTableWidgetItem(rate)
            t_item6.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 6, t_item6)

    def set_current_chart_to_page(self, source_data: str, base_option: str):
        """ 设置数据到图形区域 """
        self.chart_container.set_chart_option(source_data, base_option)






