# _*_ coding:utf-8 _*_
# @File  : price_index.py
# @Time  : 2020-11-25 16:01
# @Author: zizle
""" 价格指数窗口 """

import datetime
import json
import pandas as pd
from PyQt5.QtWidgets import (qApp, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QDateEdit, QPushButton,
                             QSplitter, QTableWidget, QHeaderView, QTableWidgetItem)
from PyQt5.QtCore import Qt, QMargins, QUrl, QDate
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtNetwork import QNetworkRequest
from widgets import TitleOptionWidget, WebChartWidget
from channels.price_index import PriceIndexChannel
from settings import EXCHANGES, SERVER_API
from utils.logger import logger
from utils.day import generate_days_of_year


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
        self.season_button = QPushButton('季节图表', self)
        self.season_button.setEnabled(False)
        title_layout.addWidget(self.season_button)

        self.option_widget = TitleOptionWidget(self)
        self.option_widget.setLayout(title_layout)
        layout.addWidget(self.option_widget)

        # 图形表格拖动区
        splitter = QSplitter(Qt.Vertical, self)
        splitter.setContentsMargins(QMargins(10, 5, 10, 5))
        # 图形区
        self.chart_container = ChartContainWidget(PriceIndexChannel(), 'file:///templates/price_index.html', self)
        splitter.addWidget(self.chart_container)
        # 表格区
        table_widget = QWidget(self)
        table_layout = QVBoxLayout()
        self.unit_label = QLabel('单位:%')
        self.unit_label.hide()
        table_layout.addWidget(self.unit_label, alignment=Qt.AlignRight | Qt.AlignTop)
        self.data_table = QTableWidget(self)
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(['日期', '价格指数', '总持仓', '总成交量'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.data_table)

        # 涨跌幅表格
        self.up_down_table = QTableWidget(self)
        self.up_down_table.verticalHeader().hide()
        self.up_down_table.horizontalHeader().hide()
        table_layout.addWidget(self.up_down_table)

        table_widget.setLayout(table_layout)

        splitter.addWidget(table_widget)
        self.up_down_table.hide()

        splitter.setSizes([self.parent().height() * 0.6, self.parent().height() * 0.4, self.parent().height() * 0.4])

        layout.addWidget(splitter)
        self.setLayout(layout)

        """ 逻辑业务部分 """
        self.source_df = None
        self.current_price_index = None
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
        # 管理季节图表信号
        self.season_button.clicked.connect(self.generate_season_chart)

    def set_current_price_index(self, index_type: str):
        """ 设置当前窗口类型 """
        if index_type not in ['weight', 'dominant']:
            return
        if self.current_price_index is not None:
            del self.current_price_index
            self.current_price_index = None
        self.current_price_index = index_type

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

    def get_min_max_date_with_variety(self):
        """ 根据品种获取最大最小时间 """
        if not self.variety_combobox.currentData():
            return
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

    def set_min_and_max_dates(self, min_date: int, max_date: int):
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

    def get_price_index_data(self):
        """ 获取价格指数数据 """
        # 还原属性
        self.season_button.setEnabled(False)
        if self.source_df is not None:
            del self.source_df
            self.source_df = None
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
            self.set_current_data_to_table(data['data'].copy())
            self.set_current_data_to_page(json.dumps(data['data']), data['base_option'])
            # 开放季节图形可点
            self.season_button.setEnabled(True)
        reply.deleteLater()

    def set_current_data_to_table(self, data_items: list):
        pass

    def set_current_data_to_page(self, source_data: str, base_option: str):
        pass

    def swap_table(self):
        """ 切换显示的表格 """
        self.data_table.setVisible(self.data_table.isHidden())
        self.up_down_table.setVisible(self.up_down_table.isHidden())
        self.unit_label.setVisible(self.unit_label.isHidden())
        self.season_button.setText('季节图表' if self.season_button.text() == '数据图表' else '数据图表')

    def generate_season_chart(self):
        """ 生成季节图形数据作图 """
        if self.source_df is None or self.current_price_index is None:
            return
        self.swap_table()
        # 生成需要的结果数据
        try:
            chart_source_data, up_down_data = self.calculate_season_result_data(self.source_df)
            print(chart_source_data)
            print(up_down_data)
            # 数据在表格展示
            self.set_data_to_up_down_table(up_down_data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)

    def set_data_to_up_down_table(self, table_data: dict):
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
            year_item = QTableWidgetItem("{}年".format(year))
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
            if avg_value and avg_value < '0':
                new_item5.setBackground(QBrush(QColor(20, 180, 56)))

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
                    weight_amplitude = round((weight_max_price - weight_min_price) * 100 / weight_min_price, 2)
                    # 计算波幅(主力)
                    dominant_min_price = month_df['dominant_price'].min()
                    dominant_max_price = month_df['dominant_price'].max()
                    dominant_amplitude = round((dominant_max_price - dominant_min_price) * 100 / dominant_min_price, 2)
                # 整理出结果
                month_up_down[str(year) + month] = {
                    'weight_up_down': weight_up_down,
                    'weight_amplitude': weight_amplitude,
                    'dominant_up_down': dominant_up_down,
                    'dominant_amplitude': dominant_amplitude
                }
                up_down_values[str(year)] = month_up_down.copy()

        return target_values, up_down_values


# 权重指数窗口
class WeightPriceWin(PriceIndexWin):

    def set_current_data_to_table(self, data_items: list):
        self.data_table.clear()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(['日期', '品种', '权重价格', '成交量合计', '持仓量合计'])
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
            t_item2 = QTableWidgetItem(format(row_item['weight_price'], ','))
            t_item2.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 2, t_item2)
            t_item3 = QTableWidgetItem(format(row_item['total_trade'], ','))
            t_item3.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 3, t_item3)
            t_item4 = QTableWidgetItem(format(row_item['total_position'], ','))
            t_item4.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 4, t_item4)

    def set_current_data_to_page(self, source_data: str, base_option: dict):
        base_option['title'] = base_option['title'].format('权重')
        base_option['price_name'] = '权重价格'
        base_option['price_name_en'] = 'weight'
        self.chart_container.set_chart_option(source_data, json.dumps(base_option))


# 主力指数窗口
class DominantPriceWin(PriceIndexWin):
    def set_current_data_to_table(self, data_items: list):
        self.data_table.clear()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(['日期', '品种', '主力价格', '成交量合计', '持仓量合计'])
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
            t_item2 = QTableWidgetItem(format(row_item['dominant_price'], ','))
            t_item2.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 2, t_item2)
            t_item3 = QTableWidgetItem(format(row_item['total_trade'], ','))
            t_item3.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 3, t_item3)
            t_item4 = QTableWidgetItem(format(row_item['total_position'], ','))
            t_item4.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row, 4, t_item4)

    def set_current_data_to_page(self, source_data: str, base_option: dict):
        base_option['title'] = base_option['title'].format('主力')
        base_option['price_name'] = '主力价格'
        base_option['price_name_en'] = 'dominant'
        self.chart_container.set_chart_option(source_data, json.dumps(base_option))
