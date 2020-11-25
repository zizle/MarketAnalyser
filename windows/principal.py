# _*_ coding:utf-8 _*_
# @File  : principal.py
# @Time  : 2020-11-25 16:03
# @Author: zizle
""" 主窗口 """

from PyQt5.QtWidgets import QMainWindow, QDesktopWidget, QLabel
from PyQt5.QtGui import QIcon
from settings import WINDOW_TITLE, SYSTEM_MENUS

from .price_position import PricePositionWin
from .price_index import PriceIndexWin


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

        """ 业务逻辑部分 """
        # 设置菜单
        self.set_menus(SYSTEM_MENUS)
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
        win = PricePositionWin()
        self.setCentralWidget(win)
        self.current_win = 11  # 价格净持率的窗口id(详见settings.py)

    def select_menu_action(self):
        """ 选择了某个菜单 """
        action = self.sender()
        action_id = getattr(action, "id")
        action_text = action.text()
        if self.current_win is not None and action_id == self.current_win:
            return
        self.setCentralWidget(self.enter_menu_window(action_id, action_text))
        self.current_win = action_id

    def enter_menu_window(self, action_id, action_text):
        """ 进入菜单选择的窗口 """
        if action_id == 11:
            page = PricePositionWin()  # 价格持仓窗口
        elif action_id == 12:  # 价格指数窗口
            page = PriceIndexWin()
        else:
            page = QLabel("该功能未开放")
        return page



