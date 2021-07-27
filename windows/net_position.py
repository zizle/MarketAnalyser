# _*_ coding:utf-8 _*_
# @File  : net_position.py
# @Time  : 2021-07-27 13:37
# @Author: zizle
import json

from PyQt5.QtCore import QDate, QUrl
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtWidgets import qApp, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, \
    QLabel, QFrame, QPushButton
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

    def query_net_position_analysis(self):
        print('查询数据')
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
        print(data)

