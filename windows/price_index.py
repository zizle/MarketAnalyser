# _*_ coding:utf-8 _*_
# @File  : price_index.py
# @Time  : 2020-11-25 16:01
# @Author: zizle
""" 价格指数窗口 """

import datetime
import json
import pandas as pd
from PyQt5.QtWidgets import (qApp, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton,
                             QSplitter, QTableWidget, QHeaderView, QTableWidgetItem, QAbstractItemView, QFileDialog,
                             QSpinBox, QMessageBox)
from PyQt5.QtCore import Qt, QMargins, QUrl, QDate
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from widgets import TitleOptionWidget, LoadingCover
from channels.price_index import PriceIndexChannel
from settings import EXCHANGES, SERVER_API, SERVER_2_0
from utils.logger import logger
from utils.day import generate_days_of_year
from utils.constant import HORIZONTAL_HEADER_STYLE, VERTICAL_SCROLL_STYLE, HORIZONTAL_SCROLL_STYLE


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

    def set_line_chart_option(self, source_data, base_option):
        """ 传入数据设置图形 """
        self.contact_channel.lineData.emit(source_data, base_option)
        self.resize_chart()

    def set_season_chart_option(self, source_data, base_option):
        """ 设置季节图形 """
        self.contact_channel.seasonData.emit(source_data, base_option)
        self.resize_chart()

    def set_price_space_chart_option(self, source_data, base_option):
        """ 设置指数区间带图形 """
        self.contact_channel.spaceData.emit(source_data, base_option)
        self.resize_chart()
        
    def resizeEvent(self, event):
        super(ChartContainWidget, self).resizeEvent(event)
        self.resize_chart()

    def resize_chart(self):
        self.contact_channel.chartResize.emit(self.width(), self.height())

    def clear_chart(self):
        self.contact_channel.clearChart.emit()


class PriceIndexWin(QWidget):
    """ 价格指数窗口 """

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
        # 切换涨跌和图形的按钮
        self.swap_data_button = QPushButton('季节图表', self)
        self.swap_data_button.setEnabled(False)
        title_layout.addWidget(self.swap_data_button)

        self.option_widget = TitleOptionWidget(self)
        self.option_widget.setLayout(title_layout)
        layout.addWidget(self.option_widget)

        # 图形表格拖动区
        self.splitter = QSplitter(Qt.Vertical, self)
        self.splitter.setContentsMargins(QMargins(0, 0, 0, 0))

        # 请求数据遮罩层(需放在splitter之后才能显示,不然估计是被splitter覆盖)
        self.loading_cover = LoadingCover()
        self.loading_cover.setParent(self)
        self.loading_cover.resize(self.parent().width(), self.parent().height())

        # 图形区
        self.loading_cover.show(text='正在加载资源')
        self.chart_container = ChartContainWidget(PriceIndexChannel(), 'file:/templates/price_index.html', self)
        self.chart_container.page().loadFinished.connect(self.page_load_finished)
        self.splitter.addWidget(self.chart_container)
        # 表格区
        table_widget = QWidget(self)
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(QMargins(0, 0, 0, 0))
        table_option_layout = QHBoxLayout()
        # 近x年的指数涨跌幅度显示
        table_option_layout.addWidget(QLabel('分析年度:', self))
        cur_year = QDate.currentDate().year()
        self.start_year = QSpinBox(self)
        self.start_year.setMinimum(2003)
        self.start_year.setMaximum(2050)
        self.start_year.setSuffix('年')
        self.start_year.setValue(cur_year - 3)
        table_option_layout.addWidget(self.start_year)
        table_option_layout.addWidget(QLabel('至', self))

        self.end_year = QSpinBox(self)
        self.end_year.setMinimum(2003)
        self.end_year.setMaximum(2050)
        self.end_year.setSuffix('年')
        self.end_year.setValue(cur_year)
        table_option_layout.addWidget(self.end_year)

        self.index_updown_button = QPushButton('指数分析', self)
        table_option_layout.addWidget(self.index_updown_button)
        # 全品种的涨跌振幅
        self.all_updown = QPushButton('年度涨跌', self)
        table_option_layout.addWidget(self.all_updown)

        # 指定月份涨跌振幅
        self.pointer_month = QDateEdit(self)
        self.pointer_month.setDate(QDate.currentDate())
        self.pointer_month.setDisplayFormat('yyyy-MM')
        self.pointer_month.setCalendarPopup(True)
        table_option_layout.addWidget(self.pointer_month)
        self.month_updown = QPushButton('月度涨跌', self)
        table_option_layout.addWidget(self.month_updown)

        table_option_layout.addStretch()

        self.unit_label = QLabel('单位:%')
        self.unit_label.hide()
        table_option_layout.addWidget(self.unit_label)

        self.export_button = QPushButton('导出EXCEL', self)
        self.export_button.setEnabled(False)
        table_option_layout.addWidget(self.export_button)

        table_layout.addLayout(table_option_layout)
        self.data_table = QTableWidget(self)
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(['日期', '价格指数', '总持仓', '总成交量'])
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.data_table.setFocusPolicy(Qt.NoFocus)
        self.data_table.horizontalHeader().setStyleSheet(HORIZONTAL_HEADER_STYLE)
        self.data_table.horizontalScrollBar().setStyleSheet(HORIZONTAL_SCROLL_STYLE)
        self.data_table.verticalScrollBar().setStyleSheet(VERTICAL_SCROLL_STYLE)
        self.data_table.verticalHeader().hide()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.verticalHeader().setDefaultSectionSize(18)  # 设置行高(与下行代码同时才生效)
        self.data_table.verticalHeader().setMinimumSectionSize(18)
        table_layout.addWidget(self.data_table)

        # 涨跌幅表格
        font = QFont()
        font.setPointSize(9)
        self.up_down_table = QTableWidget(self)
        self.up_down_table.verticalHeader().hide()
        self.up_down_table.horizontalHeader().hide()
        self.up_down_table.setFont(font)
        self.up_down_table.horizontalHeader().setStyleSheet(HORIZONTAL_HEADER_STYLE)
        self.up_down_table.horizontalScrollBar().setStyleSheet(HORIZONTAL_SCROLL_STYLE)
        self.up_down_table.verticalScrollBar().setStyleSheet(VERTICAL_SCROLL_STYLE)
        self.up_down_table.verticalHeader().setDefaultSectionSize(18)  # 设置行高(与下行代码同时才生效)
        self.up_down_table.verticalHeader().setMinimumSectionSize(18)
        self.up_down_table.setFocusPolicy(Qt.NoFocus)
        table_layout.addWidget(self.up_down_table)

        table_widget.setLayout(table_layout)

        self.splitter.addWidget(table_widget)
        self.up_down_table.hide()

        self.splitter.setSizes([self.parent().height() * 0.6, self.parent().height() * 0.4, self.parent().height() * 0.4])

        self.splitter.setFixedWidth(self.parent().width() * 0.8)

        layout.addWidget(self.splitter, alignment=Qt.AlignHCenter)
        self.setLayout(layout)
        self.data_table.setObjectName('dataTable')
        self.data_table.setAlternatingRowColors(True)
        self.up_down_table.setObjectName('upDownTable')
        self.setStyleSheet(
            "#dataTable{selection-color:rgb(80,100,200);selection-background-color:rgb(220,220,220);"
            "alternate-background-color:rgb(230,254,238);gridline-color:rgb(60,60,60)}"
            "#upDownTable{selection-color:rgb(252,252,252);selection-background-color:rgb(33,66,131);"
            "gridline-color:rgb(60,60,60)}"
        )

        """ 逻辑业务部分 """
        self.table_head_font = QFont()
        self.table_head_font.setBold(True)
        self.source_df = None  # 源数据
        self.current_price_index = None  # 当前要显示的数据类型
        self.current_show = 'source_price'  # 当前显示的界面 `source_price`为显示价格；`amplitude`为涨跌与波幅
        self.network_manager = getattr(qApp, 'network')
        # 关联交易所改变信号
        self.exchange_combobox.currentTextChanged.connect(self.get_variety_with_exchange)
        # 关联品种变化信号
        self.variety_combobox.currentTextChanged.connect(self.get_min_max_date_with_variety)
        # 添加交易所
        for exchange_item in EXCHANGES:
            self.exchange_combobox.addItem(exchange_item['name'], exchange_item['id'])
        # 关联开始计算信号
        self.analysis_button.clicked.connect(self.get_price_index_data)
        # 关联季节图表信号
        self.swap_data_button.clicked.connect(self.swap_data_show_style)
        # 导出数据信号
        self.export_button.clicked.connect(self.export_result_to_excel)
        # 点击指数分析
        self.index_updown_button.clicked.connect(self.to_analysis_price)  # 指数分析,即区间带分析
        # 点击全品种涨跌幅
        self.all_updown.clicked.connect(self.to_get_all_variety_updown)  # 全品种的指定年份涨跌振幅情况
        # 查询月份涨跌
        self.month_updown.clicked.connect(self.to_get_month_updown)  # 查询全品种指定月份的涨跌振幅数据

    def to_get_month_updown(self):
        cur_date = datetime.datetime.strptime(self.pointer_month.text(), '%Y-%m').strftime('%Y-%m-%d')
        url = SERVER_2_0 + 'dsas/mquotes/month/updown/' + f'?date={cur_date}'
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.month_varieties_updown_reply)

    def month_varieties_updown_reply(self):
        reply = self.sender()
        if reply.error():
            logger.error('获取指定月份全品种涨跌数据 ERROR. STATUS:{}'.format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            self.table_show_month_varieties_updown(data.get('data', []))

    def table_show_month_varieties_updown(self, data):  # 显示月涨跌波幅
        # 填前2行表头
        month_list = sorted(list(set([item['month'] for item in data])))
        # 填写涨跌幅表格的数据
        self.up_down_table.clear()
        self.up_down_table.setRowCount(2)
        col_count = 2 * len(month_list) + 1
        self.up_down_table.setColumnCount(col_count)
        self.up_down_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        variety_name = QTableWidgetItem('品种')
        variety_name.setTextAlignment(Qt.AlignCenter)
        self.up_down_table.setItem(0, 0, variety_name)
        self.up_down_table.setSpan(0, 0, 2, 1)
        month_index = 0
        for col in range(1, col_count):
            if col % 2 == 1:
                self.up_down_table.setSpan(0, col, 1, 2)

                year_item = QTableWidgetItem(f'{month_list[month_index]}')
                year_item.setTextAlignment(Qt.AlignCenter)
                self.up_down_table.setItem(0, col, year_item)
                up_down_name = QTableWidgetItem('涨跌')
                up_down_name.setTextAlignment(Qt.AlignCenter)
                up_down_name.setData(Qt.UserRole, {'op': 'zd', 'month': month_list[month_index]})
                self.up_down_table.setItem(1, col, up_down_name)
                amplitude_name = QTableWidgetItem('波幅')
                amplitude_name.setData(Qt.UserRole, {'op': 'zf', 'month': month_list[month_index]})
                amplitude_name.setTextAlignment(Qt.AlignCenter)
                self.up_down_table.setItem(1, col + 1, amplitude_name)

                month_index += 1

        # 填品种
        variety_list = sorted(list(set([item['variety_en'] for item in data])))
        for variety in variety_list:
            cur_row = self.up_down_table.rowCount()
            self.up_down_table.insertRow(cur_row)
            v_item = QTableWidgetItem(variety)
            v_item.setTextAlignment(Qt.AlignCenter)
            self.up_down_table.setItem(cur_row, 0, v_item)

        # 填数据
        for variety_item in data:
            # 获取该item应该填的的起始行和列
            pos_row, pos_column = self.get_up_down_month_pos(variety_item['variety_en'], variety_item['month'])
            zd = variety_item['zd']
            zd_item = QTableWidgetItem(zd if zd == '-' else '%.2f%%' % (zd * 100))
            zd_item.setTextAlignment(Qt.AlignCenter)
            if zd != '-' and zd < 0:
                zd_item.setBackground(QBrush(QColor(20, 188, 80)))
                zd_item.setForeground(QBrush(QColor(255, 255, 255)))
            elif zd != '-' and zd > 0:
                zd_item.setBackground(QBrush(QColor(216, 40, 46)))
                zd_item.setForeground(QBrush(QColor(255, 255, 255)))
            self.up_down_table.setItem(pos_row, pos_column, zd_item)
            zf = variety_item['zf']
            zf_item = QTableWidgetItem(zf if zf == '-' else '%.2f%%' % (zf * 100))
            zf_item.setTextAlignment(Qt.AlignCenter)
            self.up_down_table.setItem(pos_row, pos_column + 1, zf_item)

        # 显示表格
        self.up_down_table.show()
        self.data_table.hide()
        # self.export_button.setEnabled(True)

    def to_get_all_variety_updown(self):
        start_year = self.start_year.value()
        end_year = self.end_year.value()
        if start_year >= end_year:
            QMessageBox.critical(self, '错误', '起始年份需小于结束年份!')
            return
        url = SERVER_2_0 + 'dsas/mquotes/year/updown/' + f'?ys={start_year}&ye={end_year}'
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.all_variety_updown_reply)

    def all_variety_updown_reply(self):
        reply = self.sender()
        if reply.error():
            logger.error('获取近x年全品种涨跌数据 ERROR. STATUS:{}'.format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            self.table_show_all_variety_updown(data.get('data', []))

    def table_show_all_variety_updown(self, data):
        # 填前2行表头
        year_list = sorted(list(set([item['year'] for item in data])))
        # 填写涨跌幅表格的数据
        self.up_down_table.clear()
        self.up_down_table.setRowCount(2)
        col_count = 2 * len(year_list) + 1
        self.up_down_table.setColumnCount(col_count)
        self.up_down_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        variety_name = QTableWidgetItem('品种')
        variety_name.setTextAlignment(Qt.AlignCenter)
        self.up_down_table.setItem(0, 0, variety_name)
        self.up_down_table.setSpan(0, 0, 2, 1)
        year_index = 0
        for col in range(1, col_count):
            if col % 2 == 1:
                self.up_down_table.setSpan(0, col, 1, 2)

                year_item = QTableWidgetItem(f'{year_list[year_index]}年')
                year_item.setTextAlignment(Qt.AlignCenter)
                self.up_down_table.setItem(0, col, year_item)
                up_down_name = QTableWidgetItem('涨跌')
                up_down_name.setTextAlignment(Qt.AlignCenter)
                up_down_name.setData(Qt.UserRole, {'op': 'zd', 'year': year_list[year_index]})
                self.up_down_table.setItem(1, col, up_down_name)
                amplitude_name = QTableWidgetItem('波幅')
                amplitude_name.setData(Qt.UserRole, {'op': 'zf', 'year': year_list[year_index]})
                amplitude_name.setTextAlignment(Qt.AlignCenter)
                self.up_down_table.setItem(1, col + 1, amplitude_name)

                year_index += 1
        # # 填数据
        # for index, item in enumerate(data):
        #     row = index + 2
        #     item = QTableWidgetItem(str(item['variety_en']))
        #     item.setTextAlignment(Qt.AlignCenter)
        #     self.up_down_table.setItem(row, 0, item)

        # 填品种
        variety_list = sorted(list(set([item['variety_en'] for item in data])))
        for variety in variety_list:
            cur_row = self.up_down_table.rowCount()
            self.up_down_table.insertRow(cur_row)
            v_item = QTableWidgetItem(variety)
            v_item.setTextAlignment(Qt.AlignCenter)
            self.up_down_table.setItem(cur_row, 0, v_item)

        # 填数据
        for variety_item in data:
            # 获取该item应该填的的起始行和列
            pos_row, pos_column = self.get_up_down_table_pos(variety_item['variety_en'], variety_item['year'])
            zd = variety_item['zd']
            zd_item = QTableWidgetItem(zd if zd == '-' else '%.2f%%' % (zd * 100))
            zd_item.setTextAlignment(Qt.AlignCenter)
            if zd != '-' and zd < 0:
                zd_item.setBackground(QBrush(QColor(20, 188, 80)))
                zd_item.setForeground(QBrush(QColor(255, 255, 255)))
            elif zd != '-' and zd > 0:
                zd_item.setBackground(QBrush(QColor(216, 40, 46)))
                zd_item.setForeground(QBrush(QColor(255, 255, 255)))
            self.up_down_table.setItem(pos_row, pos_column, zd_item)
            zf = variety_item['zf']
            zf_item = QTableWidgetItem(zf if zf == '-' else '%.2f%%' % (zf * 100))
            zf_item.setTextAlignment(Qt.AlignCenter)
            self.up_down_table.setItem(pos_row, pos_column + 1, zf_item)

        # 显示表格
        self.up_down_table.show()
        self.data_table.hide()
        # self.export_button.setEnabled(True)

    def get_up_down_table_pos(self, variety, year):
        pos_row, pos_column = -1, -1
        row_count = self.up_down_table.rowCount()
        column_count = self.up_down_table.columnCount()
        for row in range(2, row_count):
            pos_column = -1
            variety_item = self.up_down_table.item(row, 0)
            if variety_item.text() == variety:
                pos_row = row
            for col in range(1, column_count, 2):
                column_item = self.up_down_table.item(1, col)
                col_data = column_item.data(Qt.UserRole)
                if col_data['year'] == year:
                    pos_column = col
                    break
        return pos_row, pos_column

    def get_up_down_month_pos(self, variety, month):
        pos_row, pos_column = -1, -1
        row_count = self.up_down_table.rowCount()
        column_count = self.up_down_table.columnCount()
        for row in range(2, row_count):
            pos_column = -1
            variety_item = self.up_down_table.item(row, 0)
            if variety_item.text() == variety:
                pos_row = row
            for col in range(1, column_count, 2):
                column_item = self.up_down_table.item(1, col)
                col_data = column_item.data(Qt.UserRole)
                if col_data['month'] == month:
                    pos_column = col
                    break
        return pos_row, pos_column

    def to_analysis_price(self):
        start_year = self.start_year.value()
        end_year = self.end_year.value()
        if start_year >= end_year:
            QMessageBox.critical(self, '错误', '起始年份需小于结束年份!')
            return
        url = SERVER_2_0 + 'dsas/mquotes/year/extreme/?ys={}&ye={}&variety={}'.format(
            start_year, end_year, self.variety_combobox.currentData()
        )
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.price_analysis_reply)

    def price_analysis_reply(self):
        reply = self.sender()
        if reply.error():
            logger.error('获取近x年指数分析数据 ERROR. STATUS:{}'.format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            # print(data)
            # 将数据绘制成图形
            if self.current_price_index == 'dominant':
                title = f'{self.variety_combobox.currentText()}主力指数区间分析'
            elif self.current_price_index == 'weight':
                title = f'{self.variety_combobox.currentText()}权重指数区间分析'
            else:
                title = f'{self.variety_combobox.currentText()}未知指数区间分析'
            base_option = {'title': title}
            source_data = data.get('data', [])
            self.chart_container.set_price_space_chart_option(json.dumps(source_data), json.dumps(base_option))

    def resizeEvent(self, event):
        super(PriceIndexWin, self).resizeEvent(event)
        self.splitter.setFixedWidth(self.parent().width() * 0.8)
        self.loading_cover.resize(self.parent().width(), self.parent().height())

    def page_load_finished(self):
        # self.loading_cover.hide()
        pass

    def clear_contents(self):
        """ 清除图形和表格 """
        self.chart_container.clear_chart()
        self.data_table.clearContents()
        self.data_table.setRowCount(0)
        self.up_down_table.clear()
        self.up_down_table.setRowCount(0)
        self.up_down_table.setColumnCount(0)

    def show_loading(self, show_text):
        """ 显示正在请求数据 """
        # 请求数据
        self.loading_cover.show(text=show_text)
        self.analysis_button.setEnabled(False)
        self.swap_data_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.clear_contents()

    def loading_finished(self):
        """ 请求数据结束 """
        self.loading_cover.hide()
        self.analysis_button.setEnabled(True)

    def hide_price_analysis(self):  # 隐藏指数分析功能
        if self.current_price_index == 'weight':
            self.index_updown_button.hide()
            self.all_updown.hide()
        elif self.current_price_index == 'dominant':
            self.index_updown_button.show()
            self.all_updown.show()
        else:
            pass

    def set_current_price_index(self, index_type: str):
        """ 设置当前窗口类型 """
        if index_type not in ['weight', 'dominant']:
            return
        if self.current_price_index is not None:
            del self.current_price_index
            self.current_price_index = None
        self.current_price_index = index_type

        self.hide_price_analysis()

    def swap_data_show_style(self, init_flag):
        """ 转换数据显示
        :param init_flag: 按钮点击会传入一个False，初始显示默认传入True
        """
        if self.current_price_index is None:
            return
        if init_flag:
            self.set_current_data_to_page()
            self.set_current_data_to_table()
            self.up_down_table.hide()
            self.data_table.show()
            self.current_show = 'source_price'
            self.swap_data_button.setText('季节图表')
            return
        # 非初始显示就是切换
        if self.current_show == 'source_price':
            # 切换为波幅
            self.generate_season_chart()
            self.data_table.hide()
            self.up_down_table.show()
            self.current_show = 'amplitude'
            self.swap_data_button.setText('数据图表')
        elif self.current_show == 'amplitude':
            # 切换为价格数据
            self.set_current_data_to_page()
            self.set_current_data_to_table()
            self.data_table.show()
            self.up_down_table.hide()
            self.current_show = 'source_price'
            self.swap_data_button.setText('季节图表')
        else:
            pass

    def get_variety_with_exchange(self):
        """ 获取交易所下的所有品种 """
        self.show_loading('正在获取品种')
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

    def get_min_max_date_with_variety(self):
        """ 根据品种获取最大最小时间 """
        if not self.variety_combobox.currentData():
            return
        self.show_loading('正在获取日期范围')
        url = SERVER_API + 'price-index-dates/?variety_en={}'.format(self.variety_combobox.currentData())
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.min_max_date_reply)

    def min_max_date_reply(self):
        reply = self.sender()
        if reply.error():
            logger.error('GET MIN & MAX DATE WITH VARIETY ERROR, STATUS:{}'.format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            min_max_date = data["dates"]
            self.set_min_and_max_dates(min_max_date['min_date'], min_max_date['max_date'])
        reply.deleteLater()
        self.loading_finished()

    def set_min_and_max_dates(self, min_date: int, max_date: int):
        """ 设置最大最小日期 """
        if not min_date or not max_date:
            self.analysis_button.setEnabled(False)
            self.swap_data_button.setEnabled(False)
            return
        min_date = datetime.datetime.fromtimestamp(min_date)
        max_date = datetime.datetime.fromtimestamp(max_date)
        q_min_date = QDate(min_date.year, min_date.month, min_date.day)
        q_max_date = QDate(max_date.year, max_date.month, max_date.day)
        self.start_date.setDateRange(q_min_date, q_max_date)
        self.start_date.setDate(q_min_date)
        self.end_date.setDateRange(q_min_date, q_max_date)
        self.end_date.setDate(q_max_date)

    def get_price_index_data(self):
        """ 获取价格指数数据 """
        # 还原属性
        self.swap_data_button.setEnabled(False)
        self.export_button.setEnabled(False)
        if self.source_df is not None:
            del self.source_df
            self.source_df = None
        self.show_loading('正在获取数据资源')
        # 获取条件
        min_date = int(datetime.datetime.strptime(self.start_date.text(), '%Y-%m-%d').timestamp())
        max_date = int(datetime.datetime.strptime(self.end_date.text(), '%Y-%m-%d').timestamp())
        url = SERVER_API + 'price-index/?variety_en={}&min_date={}&max_date={}'.format(
            self.variety_combobox.currentData(), min_date, max_date
        )
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.price_index_data_reply)

    def price_index_data_reply(self):
        """ 得到价格指数数据 """
        reply = self.sender()
        if reply.error():
            logger.error("GET PRICE INDEX DATA ERROR. STATUS:{}".format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            # 将数据转为df保存到对象属性中
            self.source_df = pd.DataFrame(data['data'], columns=['date', 'variety_en', 'total_position', 'total_trade',
                                                                 'dominant_price', 'weight_price'])
            self.swap_data_show_style(True)
            # 开放季节图形可点
            self.swap_data_button.setEnabled(True)
            # 开放导出数据
            self.export_button.setEnabled(True)
        reply.deleteLater()
        self.loading_finished()

    def set_current_data_to_table(self):
        if self.source_df is None:
            return
        self.data_table.clear()
        self.data_table.setColumnCount(5)
        if self.current_price_index == 'weight':
            self.data_table.setHorizontalHeaderLabels(['日期', '品种', '权重价格', '成交量合计', '持仓量合计'])
            price_key = 'weight_price'
        else:
            self.data_table.setHorizontalHeaderLabels(['日期', '品种', '主力价格', '成交量合计', '持仓量合计'])
            price_key = 'dominant_price'
        data_items = self.source_df.to_dict(orient='records')
        self.data_table.setRowCount(len(data_items))
        # 反序
        data_items.reverse()

        for row, row_item in enumerate(data_items):
            t_item0 = QTableWidgetItem(row_item['date'])
            t_item0.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 0, t_item0)
            t_item1 = QTableWidgetItem(row_item['variety_en'])
            t_item1.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 1, t_item1)
            t_item2 = QTableWidgetItem(format(row_item[price_key], ','))
            t_item2.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 2, t_item2)
            t_item3 = QTableWidgetItem(format(row_item['total_trade'], ','))
            t_item3.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 3, t_item3)
            t_item4 = QTableWidgetItem(format(row_item['total_position'], ','))
            t_item4.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 4, t_item4)

    def set_current_data_to_page(self):
        if self.source_df is None:
            return
        base_option = dict()
        source_data = self.source_df.to_dict(orient='records')
        name, name_en = ('权重', 'weight') if self.current_price_index == 'weight' else ('主力', 'dominant')
        base_option['title'] = '{}价格指数'.format(name)
        base_option['price_name'] = '{}价格'.format(name)
        base_option['price_name_en'] = name_en
        self.chart_container.set_line_chart_option(json.dumps(source_data), json.dumps(base_option))

    def generate_season_chart(self):
        """ 生成季节图形数据作图 """
        if self.source_df is None or self.current_price_index is None:
            return
        # 生成需要的结果数据
        chart_source_data, up_down_data = self.calculate_season_result_data(self.source_df)
        # 数据在图形展示
        name = '持仓权重均价' if self.current_price_index == 'weight' else '主力合约价'
        base_option = {
            'title': '{}{}季节分析'.format(self.variety_combobox.currentText(), name),
            'price_name_en': self.current_price_index,
            'y_axis_name': name
        }
        self.chart_container.set_season_chart_option(json.dumps(chart_source_data), json.dumps(base_option))
        # 数据在表格展示
        self.set_data_to_up_down_table(up_down_data)

    def set_data_to_up_down_table(self, table_data: dict):
        """ 填充涨跌波幅表格数据 """
        self.up_down_table.clear()
        self.up_down_table.setColumnCount(25)
        self.up_down_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.up_down_table.setRowCount(len(table_data) + 2)
        self.up_down_table.setSpan(0, 0, 2, 1)
        year_name = QTableWidgetItem('年份')
        year_name.setTextAlignment(Qt.AlignCenter)
        self.up_down_table.setItem(0, 0, year_name)
        month_name = 1
        for col_index in range(1, 25):
            if col_index % 2 == 1:
                self.up_down_table.setSpan(0, col_index, 1, 2)
                month_name_item = QTableWidgetItem('{}月'.format('%02d' % month_name))
                month_name_item.setTextAlignment(Qt.AlignCenter)
                month_name_item.setFont(self.table_head_font)
                self.up_down_table.setItem(0, col_index, month_name_item)
                up_down_name = QTableWidgetItem('涨跌')
                up_down_name.setTextAlignment(Qt.AlignCenter)
                self.up_down_table.setItem(1, col_index, up_down_name)
                amplitude_name = QTableWidgetItem('波幅')
                amplitude_name.setTextAlignment(Qt.AlignCenter)
                self.up_down_table.setItem(1, col_index + 1, amplitude_name)
                month_name += 1
        # 填充具体数值
        up_down_key = 'weight_up_down' if self.current_price_index == 'weight' else 'dominant_up_down'
        amplitude_key = 'weight_amplitude' if self.current_price_index == 'weight' else 'dominant_amplitude'
        row_index = 2
        for year, year_dict in table_data.items():
            # 0列放的是年
            year_item = QTableWidgetItem(str(year))
            year_item.setTextAlignment(Qt.AlignCenter)
            year_item.setFont(self.table_head_font)
            self.up_down_table.setItem(row_index, 0, year_item)
            month = 1
            for col in range(1, 25):  # 列， 奇数填的是涨跌，偶数填的是波幅
                # 取月的值
                month_key = "{}{}".format(year, '%02d' % month)
                month_dict = year_dict[month_key]
                if col % 2 == 1:
                    up_down_value = month_dict[up_down_key]
                    b_color = QColor(255, 255, 255)
                    if up_down_value == 0:
                        up_down = ''
                    else:
                        up_down = '%.02f' % up_down_value
                        if up_down_value > 0:
                            b_color = QColor(146, 31, 40)
                        if up_down_value < 0:
                            b_color = QColor(20, 180, 56)
                    up_down_item = QTableWidgetItem(up_down)
                    up_down_item.setTextAlignment(Qt.AlignCenter)
                    up_down_item.setBackground(QBrush(b_color))
                    up_down_item.setForeground(QBrush(QColor(252, 252, 252)))
                    self.up_down_table.setItem(row_index, col, up_down_item)
                else:
                    amplitude_value = month_dict[amplitude_key]
                    if amplitude_value == 0:
                        amplitude = ''
                    else:
                        amplitude = '%.02f' % month_dict[amplitude_key]
                    amplitude_item = QTableWidgetItem(amplitude)
                    amplitude_item.setTextAlignment(Qt.AlignCenter)
                    self.up_down_table.setItem(row_index, col, amplitude_item)
                    month += 1
            row_index += 1
        # 统计计涨，计跌个数，最大，最小值和均值
        for row_name in ['计涨', '计跌', '最大', '最小', '均值']:
            new_row = self.up_down_table.rowCount()
            self.up_down_table.insertRow(new_row)
            name_item = QTableWidgetItem(row_name)
            name_item.setTextAlignment(Qt.AlignCenter)
            name_item.setFont(self.table_head_font)
            self.up_down_table.setItem(new_row, 0, name_item)

        for col in range(1, 25):
            up_count = 0
            down_count = 0
            sum_value = 0
            sum_count = 0
            min_value = 0
            max_value = 0
            initial_flag = False
            for row in range(2, self.up_down_table.rowCount() - 5):
                # print(row, col)
                item_text = self.up_down_table.item(row, col).text()
                # print(item_text)
                if item_text:
                    column_value = float(item_text)
                    if not initial_flag:
                        min_value = column_value
                        max_value = column_value
                        initial_flag = True
                    if column_value > 0:
                        up_count += 1
                    if column_value < 0:
                        down_count += 1
                    if column_value < min_value:
                        min_value = column_value
                    if column_value > max_value:
                        max_value = column_value
                    sum_count += 1
                    sum_value += column_value
            avg_value = '' if sum_count == 0 else str(round((sum_value / sum_count), 2))
            table_row_count = self.up_down_table.rowCount()
            if col % 2 == 0:  # 波幅列无需计个数
                up_count = down_count = '-'
            new_item1 = QTableWidgetItem(str(up_count))
            new_item1.setTextAlignment(Qt.AlignCenter)
            self.up_down_table.setItem(table_row_count - 5, col, new_item1)
            new_item2 = QTableWidgetItem(str(down_count))
            new_item2.setTextAlignment(Qt.AlignCenter)
            self.up_down_table.setItem(table_row_count - 4, col, new_item2)
            new_item3 = QTableWidgetItem(str(max_value))
            new_item3.setTextAlignment(Qt.AlignCenter)
            self.up_down_table.setItem(table_row_count - 3, col, new_item3)
            new_item4 = QTableWidgetItem(str(min_value))
            new_item4.setTextAlignment(Qt.AlignCenter)
            self.up_down_table.setItem(table_row_count - 2, col, new_item4)
            new_item5 = QTableWidgetItem(str(avg_value))
            new_item5.setTextAlignment(Qt.AlignCenter)
            if avg_value and avg_value > '0':
                new_item5.setBackground(QBrush(QColor(146, 31, 40)))
                new_item5.setForeground(QBrush(QColor(254, 254, 254)))
            if avg_value and avg_value < '0':
                new_item5.setBackground(QBrush(QColor(20, 180, 56)))
                new_item5.setForeground(QBrush(QColor(254, 254, 254)))
            self.up_down_table.setItem(table_row_count - 1, col, new_item5)

    @staticmethod
    def calculate_season_result_data(source_df: pd.DataFrame):
        """ 计算处理画图和涨跌波幅数据 """
        target_values = dict()
        target_values['xAxisData'] = generate_days_of_year()
        up_down_values = dict()
        min_date = source_df['date'].min()
        max_date = source_df['date'].max()
        start_year = int(min_date[:4])
        end_year = int(max_date[:4])
        weight_last_month = 0
        dominant_last_month = 0
        for year in range(start_year, end_year + 1):
            first_day_of_year = str(year) + '0101'
            end_day_of_year = str(year) + '1231'
            # 取数转为字典加入目标容器
            year_df = source_df[
                (source_df['date'] >= first_day_of_year) & (source_df['date'] <= end_day_of_year)].copy()
            # 转为月-日格式
            year_df['date'] = year_df['date'].apply(lambda x: x[4:])
            # 排序
            year_df = year_df.sort_values(['date'])
            # 加入年数据
            target_values[str(year)] = year_df.to_dict(orient='records')
            # 计算涨跌和波幅
            # 年数据取每月的数据
            month_up_down = dict()

            for month in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                month_fist_day = month + '01'
                month_last_day = month + '31'
                month_df = year_df[(year_df['date'] >= month_fist_day) & (year_df['date'] <= month_last_day)].copy()
                if month_df.empty:
                    weight_up_down = 0
                    weight_amplitude = 0
                    dominant_up_down = 0
                    dominant_amplitude = 0
                else:
                    # 计算涨跌(权重)
                    tail_weight = month_df.iat[month_df.shape[0] - 1, 5]
                    if weight_last_month == 0:
                        weight_up_down = 0
                    else:
                        weight_up_down = round((tail_weight - weight_last_month) * 100 / weight_last_month, 2)
                    weight_last_month = tail_weight
                    # 计算涨跌(主力)
                    tail_dominant = month_df.iat[month_df.shape[0] - 1, 4]
                    if dominant_last_month == 0:
                        dominant_up_down = 0
                    else:
                        dominant_up_down = round((tail_dominant - dominant_last_month) * 100 / dominant_last_month, 2)
                    dominant_last_month = tail_dominant
                    # 计算波幅(权重)
                    weight_min_price = month_df['weight_price'].min()
                    weight_max_price = month_df['weight_price'].max()
                    weight_amplitude = 0 if weight_min_price == 0 else round((weight_max_price - weight_min_price) * 100 / weight_min_price, 2)
                    # 计算波幅(主力)
                    dominant_min_price = month_df['dominant_price'].min()
                    dominant_max_price = month_df['dominant_price'].max()
                    dominant_amplitude = 0 if dominant_min_price == 0 else round((dominant_max_price - dominant_min_price) * 100 / dominant_min_price, 2)
                # 整理出结果
                month_up_down[str(year) + month] = {
                    'weight_up_down': weight_up_down,
                    'weight_amplitude': weight_amplitude,
                    'dominant_up_down': dominant_up_down,
                    'dominant_amplitude': dominant_amplitude
                }
                up_down_values[str(year)] = month_up_down.copy()

        return target_values, up_down_values

    def export_result_to_excel(self):
        """ 导出数据到excel """
        # 1 读取数据
        table_df = self.read_data_from_table()
        # 2 选择路径
        # 保存的文件名称
        if self.current_price_index == 'weight':
            name = '权重'
        elif self.current_price_index == 'dominant':
            name = '主力'
        else:
            name = ''
        data_type, op_flag = ('指数', False) if self.current_show == 'source_price' else ('涨跌波幅', True)
        filename = '{}-{}{}数据'.format(self.variety_combobox.currentText(), name, data_type)
        filepath, _ = QFileDialog.getSaveFileName(self, '保存文件', filename, 'EXCEL文件(*.xlsx *.xls)')
        # 3 导出当前数据
        if filepath:
            # 3 导出数据
            writer = pd.ExcelWriter(filepath, engine='xlsxwriter', datetime_format='YYYY-MM-DD')
            sheet_name = '{}-{}'.format(name, data_type)
            # 多级表头默认会出现一个空行,需改pandas源码,这里不做处理
            table_df.to_excel(writer, sheet_name=sheet_name, encoding='utf8', index=op_flag,
                              merge_cells=op_flag)
            if op_flag:
                work_sheets = writer.sheets[sheet_name]
                book_obj = writer.book
                format_obj = book_obj.add_format({'num_format': '0.00%', 'font_name': 'Arial', 'font_size': 9})
                work_sheets.set_column('A:Z', 6, cell_format=format_obj)
            writer.save()

    def read_data_from_table(self):
        if self.current_show == 'source_price':  # 读取data_table
            return self.read_data_table()
        elif self.current_show == 'amplitude':  # 读取up_down_table
            return self.read_up_down_table()
        else:
            return pd.DataFrame()

    def read_data_table(self):
        """ 读取源数据 """
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
                        self.data_table.item(row, col).text().replace(',', ''))
                except ValueError:
                    value = item_value
                row_list.append(value)
            value_list.append(row_list)
        return pd.DataFrame(value_list, columns=header_list)

    def read_up_down_table(self):
        """ 读取涨跌波幅表 """
        columns = pd.MultiIndex.from_product([
            ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
            ['涨跌', '波幅']
        ])
        value_list = []
        row_index = []
        for row in range(2, self.up_down_table.rowCount()):
            row_list = []
            row_index.append(self.up_down_table.item(row, 0).text())
            for col in range(1, self.up_down_table.columnCount()):
                item_value = self.up_down_table.item(row, col).text()
                try:
                    value = float(item_value) / 100  # 后面to_excel格式化为0.00%
                except ValueError:
                    value = item_value
                row_list.append(value)
            value_list.append(row_list)
        return pd.DataFrame(value_list, columns=columns, index=row_index)


# 权重指数窗口
class WeightPriceWin(PriceIndexWin):
    pass


# 主力指数窗口
class DominantPriceWin(PriceIndexWin):
    pass

