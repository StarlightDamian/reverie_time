# -*- coding: utf-8 -*-
"""
@Date: 2024/7/20 13:07
@Author: Damian
@Email: zengyuwei1995@163.com
@File: utils_data.py
@Description: 数据/文件管理
"""
import os
import shutil


def find_file(path):
    """
    功能：返回地址下的所有文件
    输出：文件名称列表
    """
    for root, dirs, files in os.walk(path):
        return files


def move(source_path, target_path):
    try:
        # 检查目标文件夹是否存在，不存在则创建
        target_dir = os.path.dirname(target_path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # 移动文件
        if os.path.exists(source_path):  # 先检查源文件是否存在
            shutil.move(source_path, target_path)
            print(f"文件移动成功：{source_path} -> {target_path}")
        else:
            print(f"源文件不存在：{source_path}")
    except Exception as e:
        print(f"文件移动失败：{e}")