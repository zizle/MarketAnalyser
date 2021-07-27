# _*_ coding:utf-8 _*_
# @File  : price_position.py
# @Time  : 2020-11-25 16:00
# @Author: zizle
""" 价格 - 净持仓窗口 """
import json
import datetime
import pandas as pd
from itertools import groupby

from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (qApp, QWidget, QHBoxLayout, QVBoxLayout, QTableWidgetItem, QLabel, QSplitter, QTableWidget,
                             QComboBox, QDateEdit, QPushButton, QHeaderView, QMessageBox, QAbstractItemView,
                             QFileDialog)
from PyQt5.QtCore import Qt, QMargins, QUrl, QDate
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from utils.logger import logger
from utils.constant import HORIZONTAL_HEADER_STYLE, HORIZONTAL_SCROLL_STYLE, VERTICAL_SCROLL_STYLE
from channels.price_postiion import ChartSourceChannel
from widgets import TitleOptionWidget, LoadingCover
from settings import EXCHANGES, SERVER_API, SERVER_2_0


class ChartContainWidget(QWebEngineView):
    def __init__(self, web_channel, file_url, *args, **kwargs):
        super(ChartContainWidget, self).__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        # 加载图形容器
        self.page().load(QUrl(file_url))  # 加载页面
        # 设置与页面信息交互的通道
        channel_qt_obj = QWebChannel(self.page())  # 实例化qt信道对象,必须传入页面参数
        self.contact_channel = web_channel  # 页面信息交互通道
        self.page().setWebChannel(channel_qt_obj)
        channel_qt_obj.registerObject("pageContactChannel", self.contact_channel)  # 信道对象注册信道，只能注册一个

    def set_chart_option(self, source_data, base_option):
        """ 传入数据设置图形 """
        self.contact_channel.chartSource.emit(source_data, base_option)
        self.resize_chart()

    def resizeEvent(self, event):
        super(ChartContainWidget, self).resizeEvent(event)
        # 重新设置图形的高度
        self.resize_chart()

    def resize_chart(self):
        self.contact_channel.chartResize.emit(self.width() * 0.8, self.height())

    def clear_chart(self):
        self.contact_channel.clearChart.emit()


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
        self.analysis_button.setEnabled(False)
        title_layout.addWidget(self.analysis_button)
        self.option_widget = TitleOptionWidget(self)
        self.option_widget.setLayout(title_layout)
        layout.addWidget(self.option_widget)

        # 图形表格拖动区
        splitter = QSplitter(Qt.Vertical, self)
        splitter.setContentsMargins(QMargins(10, 5, 10, 5))

        # 请求数据遮罩层(需放在splitter之后才能显示,不然估计是被splitter覆盖)
        self.loading_cover = LoadingCover()
        self.loading_cover.setParent(self)
        self.loading_cover.resize(self.parent().width(), self.parent().height())

        # 图形区
        self.loading_cover.show(text='正在加载资源')
        self.chart_container = ChartContainWidget(ChartSourceChannel(), 'file:/templates/price_position.html', self)
        self.chart_container.page().loadFinished.connect(self.page_load_finished)
        splitter.addWidget(self.chart_container)

        # 表格区
        self.table_widget = QWidget(self)
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(QMargins(0, 0, 0, 0))

        opt_widget = QWidget(self.table_widget)
        opt_lt = QHBoxLayout(opt_widget)
        opt_lt.setContentsMargins(0,0,0,0)
        opt_widget.setLayout(opt_lt)
        # 日期选择，全品种净持率查看
        self.all_date_edit = QDateEdit(self)
        self.all_date_edit.setCalendarPopup(True)
        self.all_date_edit.setDisplayFormat('yyyy-MM-dd')
        self.all_date_edit.setDate(QDate.currentDate())
        opt_lt.addWidget(self.all_date_edit)
        self.all_query_button = QPushButton('查询全净持率', self)
        opt_lt.addWidget(self.all_query_button)
        # 增加净持率
        self.add_net_rate = QPushButton('增加列', self)
        opt_lt.addWidget(self.add_net_rate)

        opt_lt.addStretch()
        # 导出数据按钮
        self.export_button = QPushButton('导出EXCEL', self)
        self.export_button.setEnabled(False)
        opt_lt.addWidget(self.export_button)
        opt_widget.setFixedHeight(30)
        table_layout.addWidget(opt_widget)
        self.data_table = QTableWidget(self)
        self.data_table.verticalHeader().hide()
        self.data_table.setFocusPolicy(Qt.NoFocus)
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(['日期', '收盘价', '总持仓', '多头', '空头', '净持仓', '净持仓率%'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSelectionMode(QAbstractItemView.SingleSelection)
        table_layout.addWidget(self.data_table)
        # 全品种净持仓率显示表
        self.all_table = QTableWidget(self)
        self.all_table.hide()
        table_layout.addWidget(self.all_table)

        self.table_widget.setLayout(table_layout)
        splitter.addWidget(self.table_widget)
        splitter.setSizes([self.parent().height() * 0.6, self.parent().height() * 0.4])
        layout.addWidget(splitter)

        # 设置表行高,各行颜色
        self.data_table.verticalHeader().setDefaultSectionSize(18)  # 设置行高(与下行代码同时才生效)
        self.data_table.verticalHeader().setMinimumSectionSize(18)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setObjectName('dataTable')
        self.setStyleSheet(
            "#dataTable{selection-color:rgb(80,100,200);selection-background-color:rgb(220,220,220);"
            "alternate-background-color:rgb(230,254,238);gridline-color:rgb(60,60,60)}"
        )
        # 设置表头,表滚动条样式
        self.data_table.horizontalHeader().setStyleSheet(HORIZONTAL_HEADER_STYLE)
        self.data_table.horizontalScrollBar().setStyleSheet(HORIZONTAL_SCROLL_STYLE)
        self.data_table.verticalScrollBar().setStyleSheet(VERTICAL_SCROLL_STYLE)

        self.setLayout(layout)

        """ 业务逻辑部分 """
        self.query_type = 'contract'  # 当前查询的数据类型
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
        # 关联导出数据信息
        self.export_button.clicked.connect(self.export_table_to_excel)
        # 查询全品种净持仓率的信号
        self.all_query_button.clicked.connect(self.to_query_all_position)
        # 增加净持率列的信号
        self.add_net_rate.setEnabled(False)
        self.add_net_rate.clicked.connect(self.to_add_new_column_rate)
        # 点击表头排序
        self.all_table.horizontalHeader().sectionClicked.connect(self.all_table_horizontal_clicked)

        self.current_table = 'single_contract'

    def all_table_horizontal_clicked(self, col):
        if col < 7:
            return
        self.all_table.sortItems(col)
        # 重新设置一下颜色
        for row in range(self.all_table.rowCount()):
            for col in range(self.all_table.columnCount()):
                item = self.all_table.item(row, col)
                if row % 2 == 0:
                    item.setBackground(QBrush(QColor(230, 254, 238)))
                else:
                    item.setBackground(QBrush(QColor(255, 255, 255)))

    def to_add_new_column_rate(self):  # 新增净持率列
        new_column_date = self.all_date_edit.text()
        self.show_loading("正在获取数据")
        url = SERVER_2_0 + 'dsas/price-position/?ds={}&de={}'.format(new_column_date, new_column_date)
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.new_column_data_reply)

    def new_column_data_reply(self):
        reply = self.sender()
        self.loading_finished()
        if reply.error():
            logger.error('GET NEW COLUMN NET POSTION ERROR. STATUS:{}'.format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            variety_data = data.get('data', None)
            if not variety_data:
                return
            current_columns = self.all_table.columnCount()
            self.all_table.insertColumn(current_columns)
            self.all_table.setHorizontalHeaderItem(current_columns, QTableWidgetItem(self.all_date_edit.text()))
            self.insert_column_data(variety_data)
        reply.deleteLater()

    def insert_column_data(self, data):  # 添加列数据
        # 数据转为dict形式
        rate_data = {item['variety_en']: item for item in data}
        current_column = self.all_table.columnCount() - 1
        for row in range(self.all_table.rowCount()):
            row_item = self.all_table.item(row, 0)
            variety_en = row_item.data(Qt.UserRole)['variety_en']
            data_item = rate_data.get(variety_en)
            if not data_item:
                continue
            # 计算净持率
            a = float(data_item['net_position'].replace(',', ''))
            b = float(data_item['position_volume'].replace(',', ''))
            rate = f'{round(a * 100 / b, 2)}%' if b > 0 else '-'
            display = round(a * 100 / b, 2) if b > 0 else '-'

            new_item = QTableWidgetItem(rate)
            new_item.setTextAlignment(Qt.AlignCenter)
            new_item.setData(Qt.DisplayRole, display)
            self.all_table.setItem(row, current_column, new_item)
            if row % 2 == 0:
                new_item.setBackground(QBrush(QColor(230, 254, 238)))

    def to_query_all_position(self):
        self.show_loading("正在获取数据")
        current_date = self.all_date_edit.text()
        url = SERVER_2_0 + 'dsas/price-position/?ds={}&de={}'.format(current_date, current_date)
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.all_variety_position_reply)

    def all_variety_position_reply(self):
        reply = self.sender()
        self.loading_finished()
        if reply.error():
            logger.error('GET ALL VARIETY NET POSTION ERROR. STATUS:{}'.format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            self.show_all_variety_net_position(data.get('data', []))
        reply.deleteLater()

    def show_all_variety_net_position(self, data):
        # 过滤data数据
        show_list = list(filter(lambda x: x['variety_en'] == x['contract'], data))
        self.all_table.clear()
        titles = ['日期', '品种', '主力收盘价', '总持仓量', '前20多单量', '前20空单量', '前20净持仓', '净持率%']
        columns = ['quotes_date', 'variety_name', 'close_price', 'position_volume', 'long_position', 'short_position',
                   'net_position', 'net_rate']

        self.all_table.setRowCount(len(show_list))
        self.all_table.setColumnCount(len(columns))
        self.all_table.setHorizontalHeaderLabels(titles)
        for row, p_item in enumerate(show_list):
            for col, key in enumerate(columns):
                if key == 'net_rate':
                    a = float(p_item['net_position'].replace(',', ''))
                    b = float(p_item['position_volume'].replace(',', ''))
                    rate = f'{round(a * 100 / b, 2)}%' if b > 0 else '-'
                    item = QTableWidgetItem(rate)
                    display = round(a * 100 / b, 2) if b > 0 else '-'
                    item.setData(Qt.DisplayRole, display)
                else:
                    item = QTableWidgetItem(str(p_item[key]))
                item.setTextAlignment(Qt.AlignCenter)
                if row % 2 == 0:
                    item.setBackground(QBrush(QColor(230, 254, 238)))
                if col == 0:
                    item.setData(Qt.UserRole, {'variety_en': p_item['variety_en']})
                self.all_table.setItem(row, col, item)

        self.data_table.hide()
        self.all_table.show()
        self.current_table = 'all_variety'
        if len(show_list) > 0:
            self.export_button.setEnabled(True)
            self.add_net_rate.setEnabled(True)

    def resizeEvent(self, event):
        super(PricePositionWin, self).resizeEvent(event)
        self.loading_cover.resize(self.parent().width(), self.parent().height())

    def clear_contents(self):
        """ 清除图形和表格 """
        self.chart_container.clear_chart()
        self.data_table.clearContents()
        self.data_table.setRowCount(0)

    def show_loading(self, show_text):
        """ 显示正在请求数据 """
        # 请求数据
        self.loading_cover.show(text=show_text)
        self.analysis_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.clear_contents()

    def loading_finished(self):
        """ 请求数据结束 """
        self.loading_cover.hide()
        self.analysis_button.setEnabled(True)

    def page_load_finished(self):
        """ 页面加载完成 """
        # self.loading_cover.hide()
        pass

    def get_variety_with_exchange(self):
        """ 获取交易所下的所有品种 """
        self.show_loading("正在获取品种")
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
        self.show_loading('正在获取合约')
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
        # 将第一个合约进行英文与数字的分离
        if len(contracts) > 0:
            variety = [''.join(list(g)) for k, g in groupby(contracts[0]['contract'], key=lambda x: x.isdigit())]
            v = variety[0] if len(variety[0]) <= 2 else variety[0][:2]
            self.contract_combobox.addItem(v)
        for contract_item in contracts:
            self.contract_combobox.addItem(contract_item['contract'])

    def get_min_max_date_with_contract(self):
        """ 根据合约获取时间范围 """
        if not self.contract_combobox.currentText():
            return
        current_contract = self.contract_combobox.currentText()
        split_list = [''.join(list(g)) for k, g in groupby(current_contract, key=lambda x: x.isdigit())]
        if len(split_list) > 1:  # 查询的是合约
            self.query_type = 'contract'
            self.show_loading('正在获取日期范围')
            url = SERVER_API + 'price-position-dates/?contract={}'.format(self.contract_combobox.currentText())
            reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
            reply.finished.connect(self.min_max_date_reply)
        else:  # 查询的是品种
            max_date = int(datetime.datetime.strptime(datetime.datetime.today().strftime('%Y-%m-%d'), '%Y-%m-%d').timestamp())
            min_date = int(datetime.datetime.strptime(str(datetime.datetime.today().year - 3), '%Y').timestamp())
            self.set_min_and_max_date(min_date, max_date)
            self.query_type = 'variety'
            self.loading_finished()  # 加载数据结束

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
        self.loading_finished()  # 加载数据结束

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
        self.show_loading('正在获取资源数据')
        min_date = int(datetime.datetime.strptime(self.start_date.text(), '%Y-%m-%d').timestamp())
        max_date = int(datetime.datetime.strptime(self.end_date.text(), '%Y-%m-%d').timestamp())
        if self.query_type == 'contract':
            url = SERVER_API + 'price-position/?contract={}&min_date={}&max_date={}'.format(
                self.contract_combobox.currentText(), min_date, max_date
            )
        elif self.query_type == 'variety':
            url = SERVER_2_0 + 'dsas/price-position/?ds={}&de={}&c={}'.format(
                self.start_date.text(), self.end_date.text(), self.contract_combobox.currentText()
            )
        else:
            return
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.price_position_reply)

    def price_position_reply(self):
        """ 获取数据返回 """
        reply = self.sender()
        if reply.error():
            logger.error("GET PRICE-POSITION DATA ERROR. STATUS:{}".format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            if self.query_type == 'variety':
                # 处理数据,由于新版接口与旧版不一致
                for item in data['data']:
                    item['date'] = item['quotes_date'].replace('-', '')
                    item['contract'] = item['variety_en']
                    item['empty_volume'] = float(item['position_volume'].replace(',', ''))
                    item['long_position'] = float(item['long_position'].replace(',', ''))
                    item['short_position'] = float(item['short_position'].replace(',', ''))
                    del item['quotes_ts']
                    del item['position_volume']
                    del item['net_position']
                    del item['quotes_date']
            self.set_current_data_to_table(data['data'].copy())  # 数据在表格展示
            self.export_button.setEnabled(True)
            # 组合基本配置信息和源数据传递到页面
            base_option = {
                'title': '{}价格与净持率趋势图'.format(self.contract_combobox.currentText())
            }
            self.set_current_chart_to_page(json.dumps(data['data']), json.dumps(base_option))
        reply.deleteLater()
        self.loading_finished()

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
            rate = '-' if row_item['empty_volume'] == 0 else str(
                round((row_item['long_position'] - row_item['short_position']) * 100 / row_item['empty_volume'], 2))
            t_item6 = QTableWidgetItem(rate)
            t_item6.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 6, t_item6)

        self.current_table = 'single_contract'
        self.data_table.show()
        self.all_table.hide()

    def set_current_chart_to_page(self, source_data: str, base_option: str):
        """ 设置数据到图形区域 """
        self.chart_container.set_chart_option(source_data, base_option)

    def export_table_to_excel(self):
        """ 导出表格数据到excel"""
        if self.current_table == 'single_contract':
            # 1 读取表格数据:
            table_df = self.read_table_data()
            # 2 选定保存的位置
            # 保存的文件名称
            filename = '{}价格-净持率数据'.format(self.contract_combobox.currentText())
            filepath, _ = QFileDialog.getSaveFileName(self, '保存文件', filename, 'EXCEL文件(*.xlsx *.xls)')
            if filepath:
                # 3 导出数据
                writer = pd.ExcelWriter(filepath, engine='xlsxwriter', datetime_format='YYYY-MM-DD')
                table_df.to_excel(writer, sheet_name='价格-净持率', index=False, encoding='utf8')
                writer.save()
        if self.current_table == 'all_variety':
            df = self.read_all_table_data() # 读取全品种表格的数据
            # 2 选定保存的位置
            # 保存的文件名称
            filename = '{}全品种价格-净持率数据'.format(self.all_date_edit.text())
            filepath, _ = QFileDialog.getSaveFileName(self, '保存文件', filename, 'EXCEL文件(*.xlsx *.xls)')
            if filepath:
                # 3 导出数据
                writer = pd.ExcelWriter(filepath, engine='xlsxwriter', datetime_format='YYYY-MM-DD')
                df.to_excel(writer, sheet_name='全品种价格-净持率', index=False, encoding='utf8')
                writer.save()

    def read_all_table_data(self):
        header_list = []
        value_list = []
        for header_col in range(self.all_table.columnCount()):
            header_list.append(
                self.all_table.horizontalHeaderItem(header_col).text()
            )
        for row in range(self.all_table.rowCount()):
            row_list = []
            for col in range(self.all_table.columnCount()):
                item_value = self.all_table.item(row, col).text()
                try:
                    value = datetime.datetime.strptime(item_value, '%Y%m%d') if col == 0 else float(
                        self.all_table.item(row, col).text())
                except ValueError:
                    value = item_value
                row_list.append(value)
            value_list.append(row_list)
        return pd.DataFrame(value_list, columns=header_list)

    def read_table_data(self):
        """ 读取表格数据 """
        header_list = []
        value_list = []
        for header_col in range(self.data_table.columnCount()):
            header_list.append(
                self.data_table.horizontalHeaderItem(header_col).text()
            )
        for row in range(self.data_table.rowCount()):
            row_list = []
            for col in range(self.data_table.columnCount()):
                item_value = self.data_table.item(row, col).text()
                try:
                    value = datetime.datetime.strptime(item_value, '%Y%m%d') if col == 0 else float(
                        self.data_table.item(row, col).text())
                except ValueError:
                    value = item_value
                row_list.append(value)
            value_list.append(row_list)
        return pd.DataFrame(value_list, columns=header_list)

