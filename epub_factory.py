#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import json

from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox

from lib.ebook import EBook
from lib.downloader import Downloader
from lib.multi_threads import MultiThreads

from pyquery import PyQuery as pq
from cgi import escape


class DialogImporter(QDialog):
    # 插入兄弟章节信号
    insertSiblingChapterSignal = pyqtSignal(QTreeWidgetItem, str, str, str)

    # 插入子章节信号
    insertChildChapterSignal = pyqtSignal(QTreeWidgetItem, str, str, str)

    # 导入完成的信号 
    importFinishSignal = pyqtSignal()

    # 每个章节插入完成的信号
    insertOneChapter = pyqtSignal(str,str)

    def __init__(self, target):
        super(DialogImporter, self).__init__()
        loadUi('ui/chapterImporter.ui', self)

        self.root = target
        self.currentChapter=target
        self.chapterList=[]

        self.downloader=Downloader().get

        self.initUi()
        self.initSignal()

    def initUi(self):
        self.progressBar.hide()
        self.progressBar.setValue(0)

    def initSignal(self):
        self.btnOpenLocalFile.clicked.connect(self.openLocalFile)
        self.btnFetchChapterList.clicked.connect(self.fetchChapterList)
        self.btnFetchChapter.clicked.connect(self.fetchChapter)
        self.insertOneChapter.connect(self.updateProgress)

    def cancel(self):
        self.close()
        self.destroy()

    def openLocalFile(self):
        filePath, fileType = QFileDialog.getOpenFileName(
            parent=self, caption="选择网页文件", filter="HTML Files (*.html)")  # 设置文件扩展名过滤注意用双分号间隔
        if filePath:
            self.realUrl.setText('file://'+filePath)

    def query(self,realUrl,referUrl,*args):
        # 根据查询选择器查询网页中的指定元素
        content=self.downloader(realUrl,encoding=self.encoding.currentText())

        doc=pq(content, parser='html').make_links_absolute(base_url=referUrl)
        if len(args)==0:
            return doc

        result=[]
        for arg in args:
            if arg:
                r=doc(arg)
                result.append(r)
            else:
                result.append([])
        return tuple(result) if len(result)>1 else result[0]

    def updateProgress(self,title,url):
        self.chapterBrowser.append('已导入章节：'+title+' ('+url+')')
        QApplication.processEvents()    # 处理窗口事件，避免失去响应

    def updateCurrentChapter(self,chapter):
        self.currentChapter=chapter

    def showChapterList(self,target):
        html='<ol>\r\n'
        for item in target:
            title=item['title'] or '无标题'
            html+='\r\n<li>'+title+'</li>\r\n'
            if 'child'  in item and item['child']:
                html+=self.showChapterList(item['child'])
        html+='</ol>\r\n'
        return html

    def fetchChapterList(self):
        groupSel=self.chapterGroupSelector.text().strip().lower()
        linkSel=self.chapterLinkSelector.text().strip().lower()
        pagSel=self.menuPaginationSelector.text().strip().lower()
        if not linkSel.endswith('a') and linkSel:
            linkSel=linkSel+' a'
        if not pagSel.endswith('a') and pagSel:
            pagSel=pagSel+' a'

        self.chapterList=[]
        parent=self.chapterList
        child=self.chapterList
        realUrl=self.realUrl.text()
        referUrl=self.referUrl.text()
        flag=bool(groupSel or linkSel or pagSel)
        itemSel=groupSel+','+linkSel if groupSel and linkSel else groupSel+linkSel
        while flag:
            flag=False
            try:
                items,group,links,paginations=self.query(realUrl,referUrl,itemSel,groupSel,linkSel,pagSel)
            except Exception as e:
                QMessageBox.critical(self, "错误", "无法获取、解析以下网页内容：\r\n"+realUrl+'\r\n\r\n'+e.args[0], QMessageBox.Ok)
                return
            for item in items:
                if item in group:
                    url=item.attrib['href'] if 'href' in item.attrib else ''
                    section={
                        'title': pq(item).text().strip(),
                        'realUrl': url,
                        'referUrl': url,
                        'child':[]
                    }
                    parent.append(section)
                    child=section['child']
                elif item in links:
                    if 'href' in item.attrib:
                        url=item.attrib['href']
                        child.append({
                            'title': pq(item).text().strip(),
                            'realUrl': url,
                            'referUrl': url,
                            'child':None
                        })
            if paginations and 'href' in  paginations[0]:
                referUrl=paginations[0].attrib['href']
                realUrl=referUrl
                flag=True
        html=self.showChapterList(self.chapterList)
        self.chapterListBrowser.setHtml(html)

    def saveChapter(self,target,data):
        # 对象选择器
        titleSel=self.chapterTitleSelector.text().strip().lower()
        contentSel=self.chapterContentSelector.text().strip().lower()
        pagSel=self.chapterPaginationSelector.text().strip().lower()
        itemSel=titleSel+','+contentSel if titleSel and contentSel else titleSel+contentSel

        # 网页地址
        title=data['title']
        realUrl=data['realUrl']
        referUrl=data['referUrl']
        content=pq('<p></p>')
        if 'child' in data and data['child']:
            print('开始插入新卷:',title)
            self.insertSiblingChapterSignal.emit(target,title,'',realUrl)
            target=self.currentChapter
            for ch in data['child']:
                self.saveChapter(target,ch)
            return

        count=0
        flag=True
        while flag:
            flag=False
            try:
                self.chapterBrowser.append('正在抓取网页：'+realUrl)
                print('正在抓取网页：'+realUrl)
                QApplication.processEvents()    # 处理窗口事件，避免失去响应
                items,titles,contents,paginations=self.query(realUrl,referUrl,itemSel,titleSel,contentSel,pagSel)
            except Exception as e:
                print("无法获取、解析以下网页内容：\r\n"+realUrl+'\r\n'+e.args[0])
                QMessageBox.critical(self, "错误", "无法获取、解析以下网页内容：\r\n"+realUrl+'\r\n\r\n'+e.args[0], QMessageBox.Ok)
                return
            for item in items:
                if item in titles:
                    if count>0:
                        print('保存章节：',title)
                        self.insertChildChapterSignal.emit(target,title,content.html(),referUrl)
                        self.insertOneChapter.emit(title or '未命名章节',realUrl)
                    title=pq(item).text().strip()
                    content=pq('<p></p>')
                    count=0
                elif item in contents:
                    content.append(item)
                    count+=1
            if paginations and 'href' in  paginations[0]:
                referUrl=paginations[0].attrib['href']
                realUrl=referUrl
                flag=True

        if count>0:
            print('保存章节：',title)
            self.insertChildChapterSignal.emit(target,title,content.html(),data['referUrl'])
            self.insertOneChapter.emit(title or '未命名章节',realUrl)

    def fetchChapter(self):
        if not self.chapterContentSelector.text().strip():
            QMessageBox.critical(self, "错误", "请输入章节内容的选择器", QMessageBox.Ok)
        if not self.chapterList:
            self.chapterList=[{
                'title': '',
                'realUrl': self.realUrl.text(),
                'referUrl': self.referUrl.text(),
            }]
        count=0
        total=len(self.chapterList)
        self.progressBar.show()
        for item in self.chapterList:
            self.saveChapter(self.root,item)
            count+=1
            self.progressBar.setValue(count*100/total)
        QMessageBox.information(
            self, '保存完毕', '所有章节已经保存，按确定关闭当前窗口。', QMessageBox.Ok)
        self.importFinishSignal.emit()
        self.cancel()

class DialogSetStyle(QDialog):

    def __init__(self, styleFilePath):
        super(DialogSetStyle, self).__init__()

        loadUi('ui/setStyle.ui', self)
        self.initSignal()
        self.style_file = styleFilePath
        if os.path.isfile(self.style_file):
            with open(self.style_file, 'r') as f:
                self.styleEditor.setPlainText(f.read())

    def initSignal(self):
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

class DialogSetConfig(QDialog):
    saveConfigSignal = pyqtSignal(dict)

    def __init__(self, config):
        super(DialogSetConfig, self).__init__()

        loadUi('ui/setConfig.ui', self)
        self.config=config
        self.initUi()
        self.initSignal()

    def initUi(self):
        self.httpProxyEnable.setChecked(self.config['httpProxyEnable'])
        self.httpProxy.setText(self.config['httpProxy']['http'])
        self.httpsProxy.setText(self.config['httpProxy']['https'])
        self.updateUi()

    def initSignal(self):
        self.btnSaveConfig.clicked.connect(self.saveConfig)
        self.btnCancel.clicked.connect(self.cancel)
        self.httpProxyEnable.toggled.connect(self.updateUi)

    def updateUi(self):
        if self.httpProxyEnable.isChecked():
            self.httpProxy.setEnabled(True)
            self.httpsProxy.setEnabled(True)
        else:
            self.httpProxy.setEnabled(False)
            self.httpsProxy.setEnabled(False)
    
    def saveConfig(self):
        self.config['httpProxyEnable']=self.httpProxyEnable.isChecked()
        self.config['httpProxy']['http']=self.httpProxy.text()
        self.config['httpProxy']['https']=self.httpsProxy.text()
        self.saveConfigSignal.emit(self.config)
        self.cancel()

    def cancel(self):
        self.close()
        self.destroy()

class ApplicationWindow(QMainWindow):
    updateChapterSignal = pyqtSignal(QTreeWidgetItem)

    def __init__(self):
        super(ApplicationWindow, self).__init__()

        loadUi('ui/mainWindow.ui', self)
        self.cover_path = 'template/cover.jpg'
        self.style_path = 'template/style.css'
        self.config_path = 'config.json'
        # 默认配置值
        self.config={
            'httpProxyEnable':False,
            'httpProxy':{
                'http':'http://127.0.0.1:1080',
                'https':'http://127.0.0.1:1080'
            }
        }

        self.__downloader = Downloader()
        self.downloader = self.__downloader.get

        self.initUi()
        self.initSignal()
        self.loadConfig(self.config_path)

    def initUi(self):
        self.epub.clear()
        self.epub.root = QTreeWidgetItem(self.epub)
        self.epub.root.setText(0, self.bookTitle.text())
        self.cover.setIcon(QIcon(self.cover_path))
        self.statusBar.show()
        self.progressBar.hide()

    def initSignal(self):
        # 菜单项事件信号绑定
        self.actionRemoveChapter.triggered.connect(self.removeChapter)
        self.actionRemoveAllChapters.triggered.connect(self.removeAllChapters)
        self.actionInsertSiblingChapter.triggered.connect(
            self.insertSiblingChapter)
        self.actionInsertChildChapter.triggered.connect(
            self.insertChildChapter)
        self.actionSelectCover.triggered.connect(self.changeCover)
        self.actionSetStyle.triggered.connect(self.setStyle)
        self.actionSetConfig.triggered.connect(self.setConfig)
        self.actionClearCache.triggered.connect(self.clearCache)
        self.actionImportChapter.triggered.connect(self.importChapter)
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

    def disableSignal(self):
        # 菜单项事件信号绑定
        self.actionRemoveChapter.triggered.disconnect()
        self.actionRemoveAllChapters.triggered.disconnect()
        self.actionInsertSiblingChapter.triggered.disconnect()
        self.actionInsertChildChapter.triggered.disconnect()
        self.actionSelectCover.triggered.disconnect()
        self.actionSetStyle.triggered.disconnect()
        self.actionSetConfig.triggered.disconnect()
        self.actionClearCache.triggered.disconnect()
        self.actionImportChapter.triggered.disconnect()
        self.actionSaveAs.triggered.disconnect()
        self.actionExit.triggered.disconnect()
        self.actionAboutThis.triggered.disconnect()
        self.cover.clicked.disconnect()
        self.bookTitle.textChanged.disconnect()
        self.chapterTitle.textChanged.disconnect()
        self.chapterURL.textChanged.disconnect()
        self.epub.itemClicked.disconnect()
        self.chapterContent.textChanged.disconnect()

    def loadConfig(self,file_path):
        if os.path.isfile(file_path):
            with open(file_path,mode='r',encoding='utf-8') as f:
                __config=json.load(f)
            self.updateConfig(__config)

    def updateConfig(self,config):
        for key,value in config.items():
            if key in self.config:
                config[key]=value
        self.saveConfig()

    def saveConfig(self):
        with open(self.config_path,'w',encoding='utf-8') as f:
            json.dump(self.config,f,indent=4,sort_keys=True)
        if self.config['httpProxyEnable']:
            self.__downloader.proxies=self.config['httpProxy']
        else:
            self.__downloader.proxies=None

    def clearCache(self):
        reply = QMessageBox.question(self,'清除缓存','是否清除所有下载的缓存文件（包括所有网页和图片）？', QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if reply==QMessageBox.Yes:
            tempdir='temp/'
            files=os.listdir(tempdir)
            total=len(files)
            count=0
            self.statusBar.hide()
            self.progressBar.setValue(0)
            self.progressBar.show()
            for file in files:
                if os.path.isfile(os.path.join(tempdir,file)):
                    os.remove(os.path.join(tempdir,file))
                count+=1
                self.progressBar.setValue(count*100/total)
                QApplication.processEvents()
            self.progressBar.hide()
            self.statusBar.show()
            QMessageBox.information(self,'清除完成','所有缓存已经清除完毕。', QMessageBox.Ok)

    def expandAllChapters(self):
        self.epub.expandAll()

    def importChapter(self):
        # 批量导入章节
        target = self.epub.currentItem()
        if not target:
            target = self.epub.root
        self.dialogImporter = DialogImporter(target)
        self.dialogImporter.insertSiblingChapterSignal.connect(
            self.insertSiblingChapterSlot)
        self.dialogImporter.insertChildChapterSignal.connect(
            self.insertChildChapterSlot)
        self.dialogImporter.importFinishSignal.connect(self.expandAllChapters)
        self.updateChapterSignal.connect(self.dialogImporter.updateCurrentChapter)
        self.dialogImporter.downloader=self.downloader
        self.dialogImporter.show()

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

    def setConfig(self):
        self.dialogSetConfig=DialogSetConfig(self.config)
        self.dialogSetConfig.saveConfigSignal.connect(self.saveConfig)
        self.dialogSetConfig.show()

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
        self.disableSignal()
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
        self.initSignal()

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
        if not target.parent():
            self.epub.root.addChild(chapter)
        else:
            target.parent().addChild(chapter)
        self.updateChapterSignal.emit(chapter)

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
            if type(content) is str:
                content = pq(content, parser='html')
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
