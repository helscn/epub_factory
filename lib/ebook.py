#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import uuid
import requests
from pyquery import PyQuery as pq
from ebooklib import epub
from urllib.parse import urlparse, urlunparse

class EBook():
    def __init__(self, author=None, title=None, lang='zh-CN'):
        self.__book = epub.EpubBook()
        self.__book.set_identifier(str(uuid.uuid4()))
        self.__book.set_language(lang)
        if title:
            self.__book.set_title(title)
        else:
            self.__book.set_title('')
        self.__author = ''
        if author:
            self.add_author(author)
        self.__links = {}
        self.__chapters = []
        self.__chapters_count = 0
        self.__images = {}
        self.__images_count = 0
        self.__cover = True
        self.downloader = lambda url: requests.get(url).content
        self.__css = ['''
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: Microsoft Yahei, SimSun, Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
}
h2 {
     text-align: left;
     text-transform: uppercase;
     font-weight: 200;
}
ol {
        list-style-type: none;
}
ol > li:first-child {
        margin-top: 0.3em;
}
nav[epub|type~='toc'] > ol > li > ol  {
    list-style-type:square;
}
nav[epub|type~='toc'] > ol > li > ol > li {
        margin-top: 0.3em;
}
        ''']

    def add_author(self, author):
        if type(author) in (list, tuple):
            for author_name in author:
                self.__book.add_author(str(author_name))
                if self.__author:
                    self.__author += ', '+str(author_name)
                else:
                    self.__author = str(author_name)
        elif author:
            self.__book.add_author(str(author))
            if self.__author:
                self.__author += ', '+str(author)
            else:
                self.__author = str(author)
        else:
            raise ValueError('未指定书籍作者名！')

    @property
    def author(self):
        return self.__author

    @property
    def title(self):
        return self.__book.title

    @title.setter
    def title(self, value):
        self.__book.set_title(value)

    @property
    def toc(self):
        return self.__chapters

    def set_cover(self, cover):
        if type(cover) is bytes:
            self.__book.set_cover('cover.jpg', cover)
        elif os.path.isfile(cover):
            with open(cover, 'rb') as f:
                self.__book.set_cover('cover.jpg', f.read())
        else:
            self.__book.set_cover('cover.jpg', self.downloader(cover))

    def set_css(self, css):
        if os.path.isfile(css):
            with open(css, 'r') as f:
                self.__css = [f.read()]
        else:
            self.__css = [css]

    def add_css(self, css):
        if os.path.isfile(css):
            with open(css, 'r') as f:
                self.__css.append(f.read())
        else:
            self.__css.append(css)

    def add_item(self, item, display=False):
        self.__book.add_item(item)
        if display:
            self.__chapters.append(item)

    def add_image(self, path, display=False):
        # 增加图片对象，并返回书本中的图片引用地址
        if path in self.__images:
            return self.__images[path]

        if os.path.isfile(path):
            with open(path, 'rb') as f:
                content = f.read()
        else:
            content = self.downloader(path)

        ext = os.path.splitext(os.path.basename(path))[-1]
        self.__images_count += 1
        img_name = 'img%05d' % (self.__images_count)
        img_id = 'Image_%05d' % (self.__images_count)
        img_path = 'images/' + img_name + ext
        img = epub.EpubItem(uid=img_id,
                            file_name=img_path,
                            content=content)
        self.add_item(img, display=display)
        self.__images[path] = img_path
        return img_path

    def add_chapter(self, title='', content='', url=None, display=True):
        self.__chapters_count += 1
        chapter_id = 'Chapter_%05d' % (self.__chapters_count)
        chapter_name = 'ch_%05d' % (self.__chapters_count)
        chapter_path = chapter_name + '.xhtml'
        if not title:
            title = chapter_id

        if not content:
            content = pq('<p></p>')
        if type(content) is not pq:
            content = pq(content)
        if url:
            up = list(urlparse(url))
            up[5] = ''
            url = urlunparse(tuple(up))
            content.make_links_absolute(base_url=url)
            self.__links[url] = chapter_path
        for img in content('img'):
            if 'src' in img.attrib:
                src = img.attrib['src']
                img.attrib['src'] = self.add_image(src)

        chapter = epub.EpubHtml(
            uid=chapter_id, file_name=chapter_path, title=title, content=content.outer_html())
        chapter.add_link(href='style/main.css',
                         rel='stylesheet', type='text/css')
        self.add_item(chapter)
        if display:
            self.__chapters.append(chapter)
        return chapter

    def add_section(self, *arg, **kwarg):
        section = self.EBookSection(self, *arg, **kwarg)
        self.__chapters.append(section.toc)
        return section

    class EBookSection():
        def __init__(self, book, title, content=None, url=None):
            self.__book = book
            if content:
                chapter = self.__book.add_chapter(
                    title, content=content, url=url, display=False)
                self.__title = chapter
            else:
                self.__title = epub.Section(title)
            self.__chapters = []

        def add_chapter(self, *arg, **kwarg):
            chapter = self.__book.add_chapter(*arg, **kwarg, display=False)
            self.__chapters.append(chapter)
            return chapter

        def add_section(self, *arg, **kwarg):
            section = self.__book.EBookSection(self.__book, *arg, **kwarg)
            self.__chapters.append(section.toc)
            return section

        @property
        def toc(self):
            return (self.__title, self.__chapters)

    def update_links(self):
        # 更新所有网页链接，替换为本地URL地址并保留fragment书签
        for item in self.__book.get_items():
            if type(item) is epub.EpubHtml:
                content = pq(item.content)
                # 更新网页超链接
                for link in content('a'):
                    if 'href' in link.attrib:
                        href = link.attrib['href']
                        up = list(urlparse(href))
                        fragment = up[5]
                        up[5] = ''
                        url = urlunparse(tuple(up))
                        if url in self.__links:
                            up = list(urlparse(self.__links[url]))
                            up[5] = fragment
                            link.attrib['href'] = urlunparse(tuple(up))
                item.content = content.outer_html()

    def save_as(self, file_path=None):
        self.update_links()
        css = epub.EpubItem(uid="main_css",
                            file_name="style/main.css",
                            media_type="text/css",
                            content='\r\n'.join(self.__css))
        self.__book.add_item(css)
        self.__book.toc = self.__chapters
        self.__book.spine = ['nav'] + self.spine
        self.__book.add_item(epub.EpubNav())
        self.__book.add_item(epub.EpubNcx())

        if not file_path:
            file_path = "{} - {}.epub".format(
                self.author if self.author else "未知作者", self.title if self.title else "未命名书籍")
        epub.write_epub(file_path, self.__book)

    @property
    def spine(self):
        return self.__get_spine(self.__chapters)

    def __get_spine(self, chapters):
        spine = []
        for chapter in chapters:
            if type(chapter) in [list, tuple]:
                spine = spine+self.__get_spine(chapter)
            elif type(chapter) is epub.EpubHtml:
                spine.append(chapter)
        return spine

