#!/usr/bin/python3
# -*- coding: utf-8 -*-

import time
import os
import requests
import chardet
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
        self.__cookies=None
        if cookies:
            self.cookies=cookies

    @staticmethod
    def md5_hash(s):
        m = md5()
        m.update(str(s).encode('utf-8'))
        return m.hexdigest()

    @property
    def cookies(self):
        return self.__cookies

    @cookies.setter
    def cookies(self,cookies):
        if type(cookies) is requests.cookies.RequestsCookieJar:
            self.__cookies=cookies
            self.session.cookies =  self.__cookies
        elif type(cookies) is dict:
            self.__cookies=requests.utils.cookiejar_from_dict(cookies, cookiejar=None, overwrite=True)
            self.session.cookies =  self.__cookies
        else:
            raise ValueError('Unknow cookies type!')

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
        if url.startswith('file://') or os.path.isfile(url):
            url=url[7:] if url.startswith('file://') else url
            if os.path.isfile(url):
                with open(url,'rb') as f:
                    return f.read()
            else:
                raise ValueError('无法读取本地文件:{}'.format(url))
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

    def decode(self,content,encoding=None,errors='ignore'):
        if type(content) is bytes and encoding:
            if encoding.lower()=='auto':
                encoding=chardet.detect(content)['encoding']
                return content.decode(encoding=encoding,errors=errors)
        else:
            return content
            

    def get(self, url, encoding=None):
        if url.startswith('file://') or os.path.isfile(url):
            url=url[7:] if url.startswith('file://') else url
            if os.path.isfile(url):
                with open(url,'rb') as f:
                    if encoding:
                        return self.decode(f.read(),encoding)
                    else:
                        return f.read()
            else:
                raise ValueError('无法读取本地文件:{}'.format(url))
        if self.cache:
            data = self.get_cache(url)
            if data:
                if encoding:
                    return self.decode(data,encoding)
                else:
                    return data
        retry_count = 0
        while retry_count < self.retry:
            try:
                r = self.session.get(
                    url, proxies=self.proxies, timeout=self.timeout)
                if r.status_code == 200:
                    if self.cache:
                        self.cache_it(url, r.content)
                    if encoding:
                        return self.decode(r.content,encoding)
                    else:
                        return r.content
                else:
                    raise ValueError('获取网页结果状态码异常:{}'.format(r.status_code))
            except Exception as e:
                retry_count += 1
                time.sleep(self.retry_interval)
                continue
        raise ValueError('无法获取指定的网页：'+url)
