import time
import queue
import threading
import sys
import os
import uuid
import requests
from pyquery import PyQuery as pq
from ebooklib import epub
from urllib.parse import urlparse, urlunparse
from hashlib import md5


class Downloader():
    def __init__(self, timeout=5, retry=5, retry_interval=2, proxies=None, cookies=None, cache=True, cache_dir='./temp'):
        self.timeout = timeout
        self.retry = retry
        self.retry_interval = retry_interval
        self.proxies = proxies
        self.session = requests.Session()
        self.cache = cache
        self.cache_dir = cache_dir
        if cookies:
            if type(cookies) is requests.cookies.RequestsCookieJar:
                self.session.cookies = cookies
            elif type(cookies) is dict:
                self.session.cookies = requests.utils.cookiejar_from_dict(
                    cookies, cookiejar=None, overwrite=True)
            else:
                raise ValueError('Unknow cookies type!')

    @staticmethod
    def md5_hash(s):
        m = md5()
        m.update(str(s).encode('utf-8'))
        return m.hexdigest()

    def save_file(self, url, save_path):
        data = self.get(url)
        # 获取保存文件的绝对路径和文件名
        path, name = os.path.split(os.path.realpath(save_path))
        if not os.path.isdir(path):
            # 如果路径不存在则自动创建
            os.makedirs(path)
        with open(os.path.join(path, name), 'wb') as f:
            f.write(data)

    def get_cache(self, url):
        name = self.md5_hash(url)
        path = os.path.join(self.cache_dir, name)
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                return f.read()
        else:
            return None

    def is_cached(self, url):
        name = self.md5_hash(url)
        path = os.path.join(self.cache_dir, name)
        return os.path.isfile(path)

    def cache_it(self, url, content):
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)
        name = self.md5_hash(url)
        path = os.path.join(self.cache_dir, name)
        with open(path, 'wb') as f:
            f.write(content)

    def get_img(self, url):
        if self.cache:
            data = self.get_cache(url)
            if data:
                return data
        retry_count = 0
        while retry_count < self.retry:
            try:
                r = self.session.get(
                    url, proxies=self.proxies, timeout=self.timeout)
                if r.status_code == 200:
                    if 'image' in r.headers['Content-Type']:
                        if self.cache:
                            self.cache_it(url, r.content)
                        return r.content
                    return ValueError('获取图片格式不正确:{}'.format(r.headers['Content-Type']))
                else:
                    raise ValueError('获取图片结果状态码异常:{}'.format(r.status_code))
            except Exception as e:
                retry_count += 1
                # logging.error(e.args[0])
                # logging.info('正在尝试重新获取网页：'+url)
                time.sleep(self.retry_interval)
                continue
        raise ValueError('无法获取指定的图片：'+url)

    def get(self, url):
        if url.endswith('.jpg') or url.endswith('.gif'):
            return self.get_img(url)
        if self.cache:
            data = self.get_cache(url)
            if data:
                return data
        retry_count = 0
        while retry_count < self.retry:
            try:
                r = self.session.get(
                    url, proxies=self.proxies, timeout=self.timeout)
                if r.status_code == 200:
                    if self.cache:
                        self.cache_it(url, r.content)
                    return r.content
                else:
                    raise ValueError('获取网页结果状态码异常:{}'.format(r.status_code))
            except Exception as e:
                retry_count += 1
                # logging.error(e.args[0])
                # logging.info('正在尝试重新获取网页：'+url)
                time.sleep(self.retry_interval)
                continue
        raise ValueError('无法获取指定的网页：'+url)

    def get_query(self, url, pattern=None):
        data = self.get(url)
        if pattern:
            return pq(data, parser='html')(pattern)
        else:
            return pq(data, parser='html')


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
        img_name = 'img_%04d' % (self.__images_count)
        img_id = 'Image_%04d' % (self.__images_count)
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


class MultiThreads():
    def __init__(self, func, callback=None, threads=5, daemon=False):
        self.save_result = False
        self.__threads = []
        self.__lock = threading.Lock()
        self.__queue = queue.Queue()
        self.__func = func
        self.__callback = callback
        self.__task_count = 0
        self.__task_done_count = 0
        self.__results = {}
        for i in range(threads):
            worker = threading.Thread(target=self.__run, args=(self.__queue,))
            if daemon:
                worker.setDaemon(True)
            worker.start()
            self.__threads.append(worker)

    def __run(self, queue):
        while True:
            args = self.__queue.get()
            key = args[0]
            if self.save_result:
                result = self.__func(*args[1:])
                self.__results[key] = result
            if self.__callback:
                self.__callback(key, result)
            if self.__lock.acquire():
                self.__task_done_count += 1
                self.__lock.release()
            self.__queue.task_done()

    def add_task(self, *args, key=None):
        key = self.__task_count if not key else key
        args = (key,)+args
        self.__task_count += 1
        self.__queue.put(args)
        return key

    def get(self, key):
        return self.__results[key]

    def __getitem__(self, key):
        return self.__results[key]

    def __contain__(self, key):
        return key in self.__results

    def results(self):
        # 通过迭代器返回依据字典键值排序后的结果
        for key in sorted(self.__results):
            yield self.__results[key]

    @property
    def results_count(self):
        return len(self.__results)

    def clear_results(self):
        self.__results = {}

    def wait_done(self):
        self.__queue.join()
        return self.results()

    @property
    def threads(self):
        # 返回总的线程
        return self.__threads

    @property
    def task_count(self):
        # 返回总的请求任务数
        return self.__task_count

    @property
    def task_todo(self):
        # 返回未完成的任务数
        return self.__task_count - self.__task_done_count

    @property
    def task_done(self):
        # 返回当前所有任务是否已经完成的布尔值
        return (self.__task_count == self.__task_done_count)


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
