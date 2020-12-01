# _*_ coding:utf-8 _*_
# @File  : day.py
# @Time  : 2020-11-27 11:12
# @Author: zizle
import datetime


def generate_days_of_year():
    """ 生成一年的每一月每一天 """
    days_list = list()
    start_day = datetime.datetime.strptime("2020-01-01", "%Y-%m-%d")
    end_day = datetime.datetime.strptime("2020-12-31", "%Y-%m-%d")
    while start_day <= end_day:
        days_list.append(start_day.strftime("%m%d"))
        start_day += datetime.timedelta(days=1)
    return days_list
