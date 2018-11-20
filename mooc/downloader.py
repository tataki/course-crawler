#!/usr/bin/python3
# -*- coding:utf-8 -*-

import sys
import time
import os
from urllib import request

'''
 urllib.urlretrieve 的回调函数：
def callbackfunc(blocknum, blocksize, totalsize):
    @blocknum:  已经下载的数据块
    @blocksize: 数据块的大小
    @totalsize: 远程文件的大小
'''


class DownLoader(object):
    def __init__(self, path):
        self.filename = ''
        self.url = ''
        self.start_time = time.time()
        self.path_file = path

    @staticmethod
    def format_size(bytes):
        try:
            bytes = float(bytes)
            kb = bytes / 1024
        except:
            print("传入的字节格式不对")
            return "Error"
        # if kb >= 1024:
        #     M = kb / 1024
        #     if M >= 1024:
        #         G = M / 1024
        #         return "%.3fG" % (G)
        #     else:
        #         return "%.3fM" % (M)
        # else:
        #     return "%.3fK" % (kb)
        return "%.3fM" % (kb/1024)

    def schedule(self, blocknum, blocksize, totalsize):
        speed = (blocknum * blocksize) / (time.time() - self.start_time)
        # speed_str = " Speed: %.2f" % speed
        speed_str = " 速度: {}/s".format(self.format_size(speed))
        recv_size = blocknum * blocksize
        #文件大小
        recv_size_re = "%.3fM" % (float(recv_size)/1024/1024)
        totalsize_re = "%.3fM" % (float(totalsize)/1024/1024)
        # 设置下载进度条
        f = sys.stdout
        pervent = recv_size / totalsize
        percent_str = "%.2f%%" % (pervent * 100)
        n = round(pervent * 50)
        s = ('#' * n).ljust(50, '-')
        f.write('\r'+percent_str.ljust(8, ' ') + '[' + s + ']' + speed_str.ljust(16, ' ')+'['+recv_size_re+'/'+totalsize_re+']')
        f.flush()
        # time.sleep(0.1)
        # f.write('\r' , end='')

    def create_task(self, filename, url):
        self.filename = filename
        self.url = url

    def start_down(self):
        self.start_time = time.time()
        path = os.path.join(self.path_file, self.filename)
        request.urlretrieve(self.url, path, self.schedule)
