# _*_ coding:utf-8 _*_
# @File  : principal.py
# @Time  : 2020-11-25 16:03
# @Author: zizle
""" 主窗口 """

from PyQt5.QtWidgets import qApp, QMainWindow, QDesktopWidget, QLabel
from PyQt5.QtGui import QIcon, QFont, QPalette
from PyQt5.QtCore import Qt
from PyQt5.QtNetwork import QNetworkAccessManager
from settings import WINDOW_TITLE, SYSTEM_MENUS

from .price_position import PricePositionWin
from .price_index import WeightPriceWin, DominantPriceWin
from .net_position import NetPositionRateWidget


class MainWindow(QMainWindow):
    """ 程序主窗口 """

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        """ UI部分 """
        # 设置标题等
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon('src/icons/winIcon.png'))
        # 初始化大小
        available_size = QDesktopWidget().availableGeometry()  # 用户的桌面信息,来改变自身窗体大小
        available_width, available_height = available_size.width(), available_size.height()
        self.resize(available_width * 0.85, available_height * 0.88)
        # 添加菜单栏
        self.menu_bar = self.menuBar()
        # 状态栏
        self.status_bar = self.statusBar()
        self.win_name_label = QLabel('未知窗口', self)
        self.win_name_label.setFont(QFont("SimHei", 10))
        pe = QPalette()
        pe.setColor(QPalette.WindowText, Qt.gray)
        self.win_name_label.setPalette(pe)
        self.status_bar.addPermanentWidget(self.win_name_label)

        """ 业务逻辑部分 """
        # 设置菜单
        self.set_menus(SYSTEM_MENUS)

        # 给程序绑定网络请求管理器
        setattr(qApp, 'network', QNetworkAccessManager(qApp))

        # 默认显示价格净持仓的窗口
        self.current_win = None
        self.set_default_homepage()

    def set_menus(self, menu_data, parent_menu=None):
        for menu_item in menu_data:
            if menu_item["children"]:
                if parent_menu:
                    menu = parent_menu.addMenu(menu_item["name"])
                    menu.setIcon(QIcon(menu_item["icon"]))
                else:
                    menu = self.menu_bar.addMenu(menu_item["name"])
                    menu.setIcon(QIcon(menu_item["icon"]))
                menu.setObjectName("subMenu")
                self.set_menus(menu_item["children"], menu)
            else:
                if parent_menu:
                    action = parent_menu.addAction(menu_item["name"])
                    action.setIcon(QIcon(menu_item["icon"]))
                else:
                    action = self.menu_bar.addAction(menu_item["name"])
                    action.setIcon(QIcon(menu_item["icon"]))
                setattr(action, "id", menu_item['id'])
                action.triggered.connect(self.select_menu_action)

    def set_default_homepage(self):
        win = NetPositionRateWidget(self)
        self.setCentralWidget(win)
        self.current_win = 10  # 价格净持率的窗口id(详见settings.py)
        self.win_name_label.setText("净持率分析")

    def select_menu_action(self):
        """ 选择了某个菜单 """
        action = self.sender()
        action_id = getattr(action, "id")
        action_text = action.text()
        if self.current_win is not None and action_id == self.current_win:
            return
        self.setCentralWidget(self.enter_menu_window(action_id, action_text))
        self.current_win = action_id
        self.win_name_label.setText(action_text)

    def enter_menu_window(self, action_id, action_text):
        """ 进入菜单选择的窗口 """
        if action_id == 11:
            page = PricePositionWin(self)  # 价格持仓窗口
        elif action_id == 12:  # 权重价格指数窗口
            page = WeightPriceWin(self)
            page.set_current_price_index('weight')
        elif action_id == 13:  # 主力合约价格指数窗口
            page = DominantPriceWin(self)
            page.set_current_price_index('dominant')
        elif action_id == 10:  # 净持仓率分析
            page = NetPositionRateWidget(self)
        else:
            page = QLabel("该功能未开放")
        return page



