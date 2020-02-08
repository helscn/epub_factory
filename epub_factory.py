#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox

from lib.epub_creater import Downloader, EBook, MultiThreads
from pyquery import PyQuery as pq
from cgi import escape


class DialogImportFromMenu(QDialog):
    insertSiblingChapterSignal = pyqtSignal(QTreeWidgetItem, str, str, str)
    insertChildChapterSignal = pyqtSignal(QTreeWidgetItem, str, str, str)

    def __init__(self, target):
        super(DialogImportFromMenu, self).__init__()
        loadUi('ui/importFromMenu.ui', self)

        self.target = target
        self.initEvent()

    def initEvent(self):
        self.btnCancel.clicked.connect(self.cancel)

    def cancel(self):
        self.insertChildChapterSignal.emit(
            self.target, 'Title', 'Content', 'URL')
        self.close()
        self.destroy()


class DialogSetStyle(QDialog):

    def __init__(self, styleFilePath):
        super(DialogSetStyle, self).__init__()

        loadUi('ui/setStyle.ui', self)
        self.initEvent()
        self.style_file = styleFilePath
        if os.path.isfile(self.style_file):
            with open(self.style_file, 'r') as f:
                self.styleEditor.setPlainText(f.read())

    def initEvent(self):
        self.btnSaveStyle.clicked.connect(self.saveStyle)
        self.btnCancel.clicked.connect(self.cancel)

    def saveStyle(self):
        if os.path.isfile(self.style_file):
            with open(self.style_file, 'w') as f:
                f.write(self.styleEditor.toPlainText())
        self.close()
        self.destroy()

    def cancel(self):
        self.close()
        self.destroy()


class ApplicationWindow(QMainWindow):

    def __init__(self):
        super(ApplicationWindow, self).__init__()

        loadUi('ui/mainWindow.ui', self)
        self.cover_path = 'template/cover.jpg'
        self.style_path = 'template/style.css'

        self.initUi()
        self.initEvent()

    def initUi(self):
        self.epub.clear()
        self.epub.root = QTreeWidgetItem(self.epub)
        self.epub.root.setText(0, self.bookTitle.text())
        self.cover.setIcon(QIcon(self.cover_path))
        self.statusBar.show()
        self.progressBar.hide()

        # 测试章节内容
        for i in range(5):
            item = self.newChapter()
            item.setText(0, '章节'+str(i))
            item.content = '内容'+str(i)
            self.epub.root.addChild(item)

        self.epub.expandAll()

    def initEvent(self):
        # 菜单项事件信号绑定
        self.actionRemoveChapter.triggered.connect(self.removeChapter)
        self.actionRemoveAllChapters.triggered.connect(self.removeAllChapters)
        self.actionInsertSiblingChapter.triggered.connect(
            self.insertSiblingChapter)
        self.actionInsertChildChapter.triggered.connect(
            self.insertChildChapter)
        self.actionSelectCover.triggered.connect(self.changeCover)
        self.actionSetStyle.triggered.connect(self.setStyle)
        self.actionImportFromMenu.triggered.connect(self.importFromMenu)
        self.actionSaveAs.triggered.connect(self.saveAs)
        self.actionExit.triggered.connect(QCoreApplication.instance().quit)
        self.actionAboutThis.triggered.connect(self.aboutThis)

        # 封面点击事件绑定
        self.cover.clicked.connect(self.changeCover)

        # 输入框事件信号绑定
        self.bookTitle.textChanged.connect(self.titleChanged)
        self.chapterTitle.textChanged.connect(self.chapterTitleChanged)
        self.chapterURL.textChanged.connect(self.urlChanged)

        # 章节目录及内容事件绑定
        self.epub.itemClicked.connect(self.chapterClicked)
        self.chapterContent.textChanged.connect(self.chapterContentChanged)

    def disableEvent(self):
        # 菜单项事件信号绑定
        self.actionRemoveChapter.triggered.disconnect()
        self.actionRemoveAllChapters.triggered.disconnect()
        self.actionInsertSiblingChapter.triggered.disconnect()
        self.actionInsertChildChapter.triggered.disconnect()
        self.actionSelectCover.triggered.disconnect()
        self.actionSetStyle.triggered.disconnect()
        self.actionImportFromMenu.triggered.disconnect()
        self.actionSaveAs.triggered.disconnect()
        self.actionExit.triggered.disconnect()
        self.actionAboutThis.triggered.disconnect()
        self.cover.clicked.disconnect()
        self.bookTitle.textChanged.disconnect()
        self.chapterTitle.textChanged.disconnect()
        self.chapterURL.textChanged.disconnect()
        self.epub.itemClicked.disconnect()
        self.chapterContent.textChanged.disconnect()

    def importFromMenu(self):
        target = self.epub.currentItem()
        if not target:
            target = self.epub.root
        self.dialogImportFromMenu = DialogImportFromMenu(target)
        self.dialogImportFromMenu.insertSiblingChapterSignal.connect(
            self.insertSiblingChapterSlot)
        self.dialogImportFromMenu.insertChildChapterSignal.connect(
            self.insertChildChapterSlot)
        self.dialogImportFromMenu.show()

    def titleChanged(self, title):
        # 修改电子书标题
        self.epub.root.setText(0, title)
        if self.epub.currentItem() is self.epub.root:
            self.chapterTitle.setText(title)

    def chapterTitleChanged(self, title):
        # 修改章节标题
        item = self.epub.currentItem()
        if item != self.epub.root:
            item.setText(0, title)
        self.refreshChapterUi()

    def urlChanged(self, url):
        # 修改章节引用URL链接
        item = self.epub.currentItem()
        if item != self.epub.root:
            item.url = url
        self.refreshChapterUi()

    def changeCover(self):
        # 修改电子书的封面图片
        filePath, fileType = QFileDialog.getOpenFileName(
            parent=self, caption="选择书籍封面", filter="Jpg Files (*.jpg)")  # 设置文件扩展名过滤注意用双分号间隔
        if filePath:
            self.cover_path = filePath
            self.cover.setIcon(QIcon(filePath))

    def setStyle(self):
        self.dialogSetStyle = DialogSetStyle(self.style_path)
        self.dialogSetStyle.show()

    def outputChapterList(self, chapter, target=[], root=False):
        # 将所有章节内容生成为HTML列表
        count = chapter.childCount()
        if root:
            target.append('<ol>')
            for i in range(count):
                self.outputChapterList(chapter.child(i), target)
            target.append('</ol>')
            return target
        target.append('<li>'+escape(chapter.text(0))+'</li>')
        if count > 0:
            target.append('<ol>')
            for i in range(count):
                self.outputChapterList(chapter.child(i), target)
            target.append('</ol>')
        return target

    def chapterClicked(self, item, column):
        # 点击章节目录显示章节内容
        self.refreshChapterUi()

    def chapterContentChanged(self):
        # 修改章节内容
        chapter = self.epub.currentItem()
        if chapter is not self.epub.root:
            chapter.content = self.chapterContent.toHtml()
        self.refreshChapterUi()

    def refreshChapterUi(self):
        # 刷新显示章节内容
        self.disableEvent()
        chapter = self.epub.currentItem()
        if chapter:
            self.chapterTitle.setText(chapter.text(0))
            if chapter is self.epub.root:
                chapterList = self.outputChapterList(
                    self.epub.root, target=[], root=True)
                self.chapterContent.setHtml('\r\n'.join(chapterList))
                self.chapterURL.setText('')
                self.chapterTitle.setReadOnly(True)
                self.chapterContent.setReadOnly(True)
                self.chapterURL.setReadOnly(True)
            else:
                self.chapterContent.setHtml(chapter.content)
                self.chapterURL.setText(chapter.url)
                self.chapterTitle.setReadOnly(False)
                self.chapterContent.setReadOnly(False)
                self.chapterURL.setReadOnly(False)
        else:
            self.chapterTitle.setText('')
            self.chapterContent.setHtml('')
            self.chapterURL.setText('')
            self.chapterTitle.setReadOnly(True)
            self.chapterContent.setReadOnly(True)
            self.chapterURL.setReadOnly(True)
        self.initEvent()

    def newChapter(self, title=None, content=None, url=None):
        # 创建新的 TreeWidgetItem 章节
        item = QTreeWidgetItem()
        item.setText(0, title or '未命名章节')
        item.content = content or ''
        item.url = url or ''
        return item

    def insertSiblingChapter(self):
        # 在当前节点插入兄弟章节
        target = self.epub.currentItem()
        if target is self.epub.root:
            title = '第 %d 章' % (target.childCount()+1)
        else:
            title = '第 %d 章' % (target.parent().childCount()+1)
        self.insertSiblingChapterSlot(target=target, title=title)
        self.epub.expandItem(
            target if target is self.epub.root else target.parent())
        self.refreshChapterUi()

    def insertSiblingChapterSlot(self, target=None, title=None, content=None, url=None):
        if not target:
            target = self.epub.root
        chapter = self.newChapter(title=title, content=content, url=url)
        if chapter is self.epub.root:
            self.epub.root.addChild(chapter)
        else:
            target.parent().addChild(chapter)

    def insertChildChapter(self):
        # 插入子章节
        target = self.epub.currentItem()
        title = '第 %d 章' % (target.childCount()+1)
        self.insertChildChapterSlot(target=target, title=title)
        self.epub.expandItem(target)
        self.refreshChapterUi()

    def insertChildChapterSlot(self, target=None, title=None, content=None, url=None):
        if not target:
            target = self.epub.root
        chapter = self.newChapter(title=title, content=content, url=url)
        target.addChild(chapter)

    def removeChapter(self):
        # 删除选择的 TreeWidgetItem 对象
        if self.epub.currentItem() is self.epub.root:
            self.removeAllChapters()
        else:
            for item in self.epub.selectedItems():
                item.parent().removeChild(item)

    def removeAllChapters(self):
        # 删除所有章节内容
        reply = QMessageBox.critical(
            self, "警告", "是否确定要删除所有的章节内容？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            title = self.epub.root.text(0)
            self.epub.clear()
            self.epub.root = QTreeWidgetItem(self.epub)
            self.epub.root.setText(0, title)

    def outputChapters(self, chapter, target, root=False):
        # 循环迭代 TreeWidget 的所有 Item 对象

        QApplication.processEvents()    # 处理窗口事件，避免失去响应

        title = chapter.text(0)
        count = chapter.childCount()
        if root:
            for i in range(count):
                self.outputChapters(chapter=chapter.child(i), target=target)
                self.progressBar.setValue((i+1)/count*90+5)
            return target
        if hasattr(chapter, 'url'):
            url = chapter.url
        else:
            url = None
        if hasattr(chapter, 'content'):
            content = chapter.content if chapter.content else '<p></p>'
            content = pq(content, parser='html')
            if not content('body').text():
                content = None
        else:
            content = None
        if count == 0:
            target.add_chapter(title=title, content=content, url=url)
        else:
            section = target.add_section(title=title, content=content, url=url)
            for i in range(count):
                self.outputChapters(chapter=chapter.child(i), target=section)
        return target

    def saveAs(self):
        # 导出电子书保存至Epub格式文件。
        filePath, fileType = QFileDialog.getSaveFileName(
            parent=self, caption="导出Epub电子书", filter="Epub Files (*.epub)")  # 设置文件扩展名过滤注意用双分号间隔
        if not filePath:
            return

        self.statusBar.hide()
        self.progressBar.setValue(0)
        self.progressBar.show()
        try:
            # 创建Epub电子书
            book = EBook(title=self.bookTitle.text())

            # 设置下载器
            book.downloader = Downloader().get

            # 增加书籍作者
            for author in self.bookAuthor.text().split(','):
                if author.strip():
                    book.add_author(author.strip())

            # 增加封面及页面样式
            book.set_cover(self.cover_path)
            if os.path.isfile(self.style_path):
                book.set_css(self.style_path)
            self.progressBar.setValue(5)

            # 增加章节内容
            self.outputChapters(chapter=self.epub.root, target=book, root=True)

            # 保存为文件
            book.save_as(filePath)
            self.progressBar.setValue(100)

            QMessageBox.information(
                self, '保存完毕', '当前书籍内容已保存至以下文件：\r\n'+filePath, QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(
                self, '错误', '保存Epub书籍时出现错误:\r\n'+e.args[0], QMessageBox.Ok)
        self.progressBar.hide()
        self.statusBar.show()

    def aboutThis(self):
        # self.statusBar.showMessage('关于本软件的说明。',4000)
        QMessageBox.about(self,
                          '关于本软件...',
                          '本软件可以通过快速抓取网页内容来生成Epub格式电子书，您可以免费使用本软件或对其进行修改，但不可使用于商业用途。\r\n\r\n作者：helscn'
                          )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    appWindow = ApplicationWindow()
    appWindow.show()
    sys.exit(app.exec_())
