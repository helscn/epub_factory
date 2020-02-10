#!/usr/bin/python3
# -*- coding: utf-8 -*-

from lib.ebook import EBook
from lib.downloader import Downloader
from lib.multi_threads import MultiThreads

if __name__ == '__main__':

    # 创建Epub小说对象
    book = EBook(author='川原砾', title='Sword Art Online 21 Unital Ring I')
    # 设置书籍封面
    book.set_cover(
        'https://ae01.alicdn.com/kf/Hd0ca7616ad0c4b06931df9f8d4406fbfC.jpg')
    # 设置书籍的络文件下载器
    book.downloader = Downloader().get

    # 读取本地html文件
    with open('test.html', mode='r', encoding='utf-8') as f:
        doc = pq(f.read())

    # 将所有超链接改为绝对引用地址
    doc.make_links_absolute(base_url=' /')

    # 通过筛选器选择小说章节
    container = doc('div.post-container')
    tags = container('h2,p')

    # 读取小说章节内容
    title = 'Sword Art Online 21 Unital Ring I'
    content = pq('<div></div>')
    content.append(pq('<h1>'+title+'/h1'))
    count = 0
    for elm in tags:
        if elm.tag == 'p':
            content.append(elm)
            count += 1
        elif elm.tag == 'h2':
            if count > 0:
                book.add_chapter(title, content)
            title = elm.text
            content = pq('<div></div>')
            content.append(elm)
            count = 0

    if count > 0:
        book.add_chapter(title, content)

    # 将小说保存为Epub文件
    book.save_as()

    book = EBook()
    job = MultiThreads(book.test)
