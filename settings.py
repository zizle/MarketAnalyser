# _*_ coding:utf-8 _*_
# @File  : settings.py
# @Time  : 2020-11-25 16:04
# @Author: zizle
""" 程序的设置文件 """
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SERVER_API = 'http://127.0.0.1:8000/api/'
SERVER_2_0 = 'http://127.0.0.1:5000/api/'
# SERVER_2_0 = 'http://210.13.218.130:9002/api/'
SERVER_API = "http://210.13.218.130:9004/api/"

WINDOW_TITLE = '行情分析助手(网络版1.1.210707)'

SYSTEM_MENUS = [
    {'id': 1, 'name': '功能选择', 'icon': '', 'children': [
        {'id': 11, 'name': '价格-净持率', 'icon': '', 'children': None},
        {'id': 12, 'name': '权重价格指数', 'icon': '', 'children': None},
        {'id': 13, 'name': '主力合约指数', 'icon': '', 'children': None}
    ]},
]

EXCHANGES = [
    {'id': 'cffex', 'name': '中国金融期货交易所'},
    {'id': 'czce', 'name': '郑州商品交易所'},
    {'id': 'dce', 'name': '大连商品交易所'},
    {'id': 'shfe', 'name': '上海期货交易所'},
]
