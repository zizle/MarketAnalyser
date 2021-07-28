# _*_ coding:utf-8 _*_
# @File  : net_position.py
# @Time  : 2021-07-27 13:37
# @Author: zizle
import json

from PyQt5.QtCore import QDate, QUrl, Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtWidgets import qApp, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, \
    QDateEdit, \
    QLabel, QFrame, QPushButton, QAbstractItemView
from widgets import TitleOptionWidget
from settings import SERVER_2_0



class NetPositionRateWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super(NetPositionRateWidget, self).__init__(*args, **kwargs)
        lt = QVBoxLayout(self)
        lt.setContentsMargins(0, 0, 0, 0)
        self.setLayout(lt)

        # 操作头
        opt_widget = TitleOptionWidget(self)
        opt_lt = QHBoxLayout(opt_widget)
        opt_widget.setLayout(opt_lt)
        opt_widget.setFixedHeight(45)
        lt.addWidget(opt_widget)

        # 显示表格
        self.data_table = QTableWidget(self)
        self.data_table.setFrameShape(QFrame.NoFrame)
        self.data_table.verticalHeader().setDefaultSectionSize(22)
        self.data_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.data_table.setFocusPolicy(Qt.NoFocus)
        lt.addWidget(self.data_table)

        self.start_date = QDateEdit(opt_widget)
        self.start_date.setDisplayFormat('yyyy-MM-dd')
        self.start_date.setCalendarPopup(True)
        year = QDate.currentDate().year() - 3
        self.start_date.setDate(QDate(year, 1, 1))
        self.end_date = QDateEdit(opt_widget)
        self.end_date.setDisplayFormat('yyyy-MM-dd')
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        opt_lt.addWidget(QLabel('开始日期:', opt_widget))
        opt_lt.addWidget(self.start_date)
        opt_lt.addWidget(QLabel('结束日期:', opt_widget))
        opt_lt.addWidget(self.end_date)

        self.query_button = QPushButton('查询', opt_widget)
        opt_lt.addWidget(self.query_button)

        self.query_status = QLabel(self)
        self.query_status.setStyleSheet('color:rgb(233,66,66)')
        opt_lt.addWidget(self.query_status)
        opt_lt.addStretch()

        # 网管器
        self.network_manager = getattr(qApp, 'network')

        self.query_button.clicked.connect(self.query_net_position_analysis)
        self.query_net_position_analysis()

        # 点击表头排序
        self.data_table.horizontalHeader().sectionClicked.connect(self.table_horizontal_clicked)

    def table_horizontal_clicked(self, col):
        if col < 7:
            return
        self.data_table.sortItems(col)
        self.set_row_colors()

    def query_net_position_analysis(self):
        self.query_status.setText('正在查询数据,请稍候...')
        url = SERVER_2_0 + 'dsas/pos/net-rate/?ds={}&de={}'.format(self.start_date.text(), self.end_date.text())
        reply = self.network_manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(self.net_rate_position_reply)

    def net_rate_position_reply(self):
        reply = self.sender()
        if reply.error():
            self.query_status.setText('查询数据失败了!{}'.format(reply.error()))
        else:
            data = json.loads(reply.readAll().data().decode('utf8'))
            self.table_show_data(data.get('data', []))
            self.query_status.setText('查询数据成功!')

    def table_show_data(self, data):
        title = ['日期', '品种', '主力收盘价', '权重价格', '前20多单', '前20空单', '前20净持仓', '最大净持率%', '最小净持率%',
                 '当前净持率%', '百分位%']
        columns = ['quote_date', 'variety_name', 'close_price', 'weight_price', 'long_position', 'short_position',
                   'net_position', 'max_rate', 'min_rate', 'pos_rate', 'cur_pos']
        self.data_table.clear()
        self.data_table.setRowCount(len(data))
        self.data_table.setColumnCount(len(columns))
        self.data_table.setHorizontalHeaderLabels(title)
        for row, item in enumerate(data):
            for col, key in enumerate(columns):
                t_ = QTableWidgetItem()
                value = item[key]
                if key in ['max_rate', 'min_rate', 'pos_rate', 'cur_pos']:
                    t_.setText(f'{value}%')
                    t_.setData(Qt.DisplayRole, item[key])
                    if key == 'cur_pos':
                        t_.setForeground(QBrush(QColor(234, 85, 4)))
                else:
                    t_.setText(str(value))
                t_.setTextAlignment(Qt.AlignCenter)
                self.data_table.setItem(row, col, t_)
                if row % 2 == 0:
                    t_.setBackground(QBrush(QColor(221, 235, 247)))

    def set_row_colors(self):  # 设置行颜色
        row_count = self.data_table.rowCount()
        col_count = self.data_table.columnCount()
        for row in range(row_count):
            for col in range(col_count):
                item = self.data_table.item(row, col)
                if row % 2 == 0:
                    item.setBackground(QBrush(QColor(221, 235, 247)))
                else:
                    item.setBackground(QBrush(QColor(255, 255, 255)))



