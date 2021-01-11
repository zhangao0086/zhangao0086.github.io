#!/usr/bin/python3
# -*-coding:utf-8-*-

__author__ = "Bannings"

import os, logging, re

if __name__ == '__main__':
    root_directory = os.path.dirname(os.path.abspath(__file__))

    # 找出所有的 markdown 文章
    post_directory = os.path.join(root_directory, '_posts')
    posts = [os.path.join(post_directory, file) for file in os.listdir(post_directory) if file[-2:]=="md"]

    if os.path.exists("output.log"):
        os.remove("output.log")
    logging.basicConfig(filename="output.log", level=logging.DEBUG, format='%(message)s')

    # 添加别名
    for post in posts:
        with open(post, "r+", encoding="utf-8") as file:
            logging.debug(post)
            lines = file.readlines()

            alias = os.path.splitext(post)[0]
            alias = os.path.basename(alias).replace("-", "/")
            alias = alias.replace(" ", "-")
            alias = alias.replace("#", "")
            lines.insert(2, f"redirect_from: /{alias}/\n")
            
            file.seek(0)
            file.truncate()
            file.writelines(lines)
            file.flush()
    # # 移除多余的文本
    # regex = re.compile("本周选择的算法题是：\[.*?\]\(.*?\)(（.*?）)")
    # for post in posts:
    #     with open(post, "r+", encoding="utf-8") as file:
    #         logging.debug(post)
    #         lines = file.readlines()
    #         changed = False
    #         for i, line in enumerate(lines):
    #             result = regex.match(line)
    #             if result:
    #                 changed = True
    #                 start, end = result.span(1)
    #                 lines[i] = line[:start]+line[end:]
    #                 logging.debug(f" {i} {lines[i]}")
    #                 break
            
    #         if changed:
    #             file.seek(0)
    #             file.truncate()
    #             file.writelines(lines)
    #             file.flush()
    