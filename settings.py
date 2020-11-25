# _*_ coding:utf-8 _*_
# @File  : settings.py
# @Time  : 2020-11-25 16:04
# @Author: zizle
""" 程序的设置文件 """

SERVER_API = 'http://127.0.0.1:8000/'

WINDOW_TITLE = '行情分析助手(网络版1.0)'

SYSTEM_MENUS = [
    {'id': 1, 'name': '功能选择', 'icon': '', 'children': [
        {'id': 11, 'name': '价格-净持率', 'icon': '', 'children': None},
        {'id': 12, 'name': '价格指数', 'icon': '', 'children': None}
    ]},
]