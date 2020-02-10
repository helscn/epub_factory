#!/usr/bin/python3
# -*- coding: utf-8 -*-

import queue
import threading

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

