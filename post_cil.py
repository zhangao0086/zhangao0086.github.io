#!/usr/bin/python3
# -*-coding:utf-8-*-

__author__ = "Bannings"

import os, sys, datetime

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = "%H:%M:%S +0800"

def start(filename):
    posts_dir = os.path.join(os.path.dirname(__file__), '_posts')

    # 创建新的文件名
    new_date_string = datetime.datetime.today().strftime(DATE_FORMAT)
    filename = f'{new_date_string}-{filename}.md'

    # 创建新的 post
    time_string = datetime.datetime.today().strftime(TIME_FORMAT)
    post_date = f"{new_date_string} {time_string}"
    with open(os.path.join(posts_dir, filename), 'w') as file:
        file.write(template_content(post_date))

def template_content(date) -> str:
    return f'''---
layout: post
title: ""
date: {date}
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

<!--more-->

'''

if __name__ == '__main__':
    start(sys.argv[1])