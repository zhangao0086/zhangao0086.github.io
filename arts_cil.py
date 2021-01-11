#!/usr/bin/python3
# -*-coding:utf-8-*-

__author__ = "Bannings"

import os, re, datetime

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = "%H:%M:%S +0800"

def start():
    posts_dir = os.path.join(os.path.dirname(__file__), '_posts')

    # 获取当前最新的 arts post
    files = sorted(os.listdir(posts_dir))
    regex = re.compile('(.*?)-ARTS #(\d+)')
    pre_date, number = None, None
    for i in range(len(files)-1,-1,-1):
        if os.path.isfile(os.path.join(posts_dir, files[i])):
            result = regex.search(files[i])
            if result:
                datetime_string, number = result.groups()
                pre_date = datetime.datetime.strptime(datetime_string, DATE_FORMAT)
                break
    
    # 创建新的文件名
    new_date, new_number = pre_date + datetime.timedelta(days=7), str(int(number) + 1)
    new_date_string = new_date.strftime(DATE_FORMAT)
    filename = f'{new_date_string}-ARTS #{new_number}.md'

    # 创建新的 post
    time_string = datetime.datetime.today().strftime(TIME_FORMAT)
    post_date = f"{new_date_string} {time_string}"
    with open(os.path.join(posts_dir, filename), 'w') as file:
        file.write(template_content(new_number, post_date))

def template_content(number, date) -> str:
    return f'''---
layout: post
title: "ARTS #{number}"
date: {date}
categories: [ARTS]
article_type: 1
excerpt_separator: <!--more-->
typora-root-url: ../../github.io
---


# Algorithm

本周选择的算法题是：[]()。

<!--more-->

## 规则



## Solution




# Review



# Tip



# Share

'''

if __name__ == '__main__':
    start()