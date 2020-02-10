#!/usr/bin/python3
# -*- coding: utf-8 -*-

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QTreeWidgetItem

CONFIG={
    'params':[
        {
            'name':'menuURL',
            'label':'章节目录地址',
            'tips':'输入章节目录的URL'
        },
        {
            'name':'chapterPattern',
            'label':'章节目录地址',
            'tips':'输入章节目录的URL'  
        }
    ]
}

class ChapterImporterBase():
    # 插入兄弟章节信号
    insertSiblingChapterSignal = pyqtSignal(QTreeWidgetItem, str, str, str)
    # 插入子章节信号
    insertChildChapterSignal = pyqtSignal(QTreeWidgetItem, str, str, str)
    # 更新导入进度值的信号
    progressSignal = pyqtSignal([int],[float])
    # 导入完成的信号 
    importFinishSignal = pyqtSignal()

    def __init__(self,root,downloader,**kwargs):
        self.root=root
        self.downloader=downloader
        self.kwargs=kwargs

    def startImport(self,path):
        # 从指定的路径导入
        pass