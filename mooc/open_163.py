# -*- coding: utf-8 -*-
"""网易公开课"""

import time
import xml.dom.minidom
import requests

from .utils import *
from bs4 import BeautifulSoup

try:
    from Crypto.Cipher import AES
except:
    from crypto.Cipher import AES # pip install pycryptodome

CANDY = Crawler()
CONFIG = {}
FILES = {}


def get_summary(url):
    """从课程主页面获取信息"""

    res = CANDY.get(url).text
    soup=BeautifulSoup(res,'html.parser')
    links = []
    if re.match(r'https?://open.163.com/special/', url):
        names = soup.find_all('div', class_='g-container')[1]
        organization = names.find('a').string.strip()
        course = names.find('span', class_='pos').string.strip()
        list1 = soup.find('table', id='list1')
        tds = list1.find_all('td', class_="u-ctitle")
        
        for td in tds:
            a = td.find('a')
            links.append((a.get('href'), a.string))

    else:
        names = soup.find('p', class_='bread').find_all('a', class_='f-c9')
        organization = names[0].string.strip()
        course = names[1].string.strip()
        listrow = soup.find('div', class_='listrow')
        for item in listrow.find_all('div',class_='item'):
            p = item.find('p', class_='f-thide')
            if p.find('a'):
                a = p.find('a')
                links.append((a.get('href'), a.string))
            else:
                links.append((url, p.string.split(']')[-1]))

    dir_name = course_dir(course, organization)

    print(dir_name)

    CONFIG['links'] = links
    return links, dir_name

def parse_resource(resource):
    """解析资源地址和下载资源"""

    def open_decrypt(hex_string, t):
        CRYKey = {1: b"4fxGZqoGmesXqg2o", 2: b"3fxVNqoPmesAqg2o"}
        aes = AES.new(CRYKey[t], AES.MODE_ECB)
        return str(aes.decrypt(bytes.fromhex(hex_string)),encoding='gbk',errors="ignore").replace('\x08','').replace('\x06', '')

    def xmlnode2string(xml_node):
        tag_name = xml_node.tagName
        return xml_node.toxml('utf8').decode().replace('<{}>'.format(tag_name),'').replace('</{}>'.format(tag_name),'')
    
    def get_hex_urls(xml_node):
        hex_urls_dict = {}
        for node in xml_node.childNodes:
            hex_urls_list = []
            for url_hex_node in node.childNodes:
                hex_urls_list.append(xmlnode2string(url_hex_node))
            hex_urls_dict[node.tagName.lower()] = hex_urls_list
        return hex_urls_dict

    link = resource.meta
    file_name = resource.file_name
    video_info = link.replace('.html', '').split('/')[-1]
    xml_url = 'http://live.ws.126.net/movie/' + video_info[-2] + '/' + video_info[-1] + '/2_' + video_info + '.xml'
    res = CANDY.get(xml_url)
    res.encoding = 'gbk'

    data = {
        'name': '',
        'encrypt': 1,
        'flvurl': {},
        'flvurl_origin': {},
        'mp4url': {},
        'mp4url_origin': {},
        'protoVersion': 1,
        'useMp4': 1,
        'subs': {},
        }
    DOMTree = xml.dom.minidom.parseString(res.text)
    data['name'] = xmlnode2string(DOMTree.getElementsByTagName('title')[0])
    data['encrypt'] = int(xmlnode2string(DOMTree.getElementsByTagName('encrypt')[0]))
    data['flvurl'] = get_hex_urls(DOMTree.getElementsByTagName('flvUrl')[0])
    data['flvurl_origin'] = get_hex_urls(DOMTree.getElementsByTagName('flvUrlOrigin')[0])
    data['mp4url'] = get_hex_urls(DOMTree.getElementsByTagName('playurl')[0])
    data['mp4url_origin'] = get_hex_urls(DOMTree.getElementsByTagName('playurl_origin')[0])
    data['protoVersion'] = int(xmlnode2string(DOMTree.getElementsByTagName('protoVersion')[0]))
    data['useMp4'] = int(xmlnode2string(DOMTree.getElementsByTagName('useMp4')[0]))
    for sub_node in DOMTree.getElementsByTagName('subs')[0].getElementsByTagName('sub'):
        data['subs'][xmlnode2string(sub_node.getElementsByTagName('name')[0])] = xmlnode2string(sub_node.getElementsByTagName('url')[0])

    k = ''
    # 先按照默认模式选择格式，待加入格式选择后再按需选择
    if data['useMp4'] == 1:
        ext = 'mp4'
    else:
        ext = 'flv'
    k += ext + 'url'
    if data['protoVersion'] == 2:
        k += '_origin'

    resolutions = ['shd', 'hd', 'sd', 'hd', 'shd']
    for sp in resolutions[CONFIG['resolution']:]:
        if data[k].get(sp):
            hex_string = data[k][sp][0] # 有时好几个，先用第一个好了
    video_url = open_decrypt(hex_string, data['encrypt'])
    ext = '.' + video_url.split('.')[-1]

    res_print(file_name + ext)
    FILES['renamer'].write(re.search(r'(\w+\%s)'% ext, video_url).group(1), file_name, ext)
    FILES['video'].write_string(video_url)
    if not CONFIG['sub']:
        return
    WORK_DIR.change('Videos')
    for subtitle_lang, subtitle_url in data['subs'].items():
        if len(data['subs']) == 1:
            sub_name = file_name + '.srt'
        else:
            sub_name = file_name + '_' + subtitle_lang + '.srt'
        res_print(sub_name)
        CANDY.download_bin(subtitle_url, WORK_DIR.file(sub_name))

def get_resource(links):
    """获取各种资源"""

    outline = Outline()
    counter = Counter(1)

    video_list = []

    for link, name in links:
        counter.add(0)
        outline.write(name, counter, 0, sign='#')
        video_list.append(Video(counter, name, link))

    if video_list:
        rename = WORK_DIR.file('Names.txt') if CONFIG['rename'] else False
        WORK_DIR.change('Videos')
        if CONFIG['dpl']:
            playlist = Playlist()
            parse_res_list(video_list, rename, playlist.write, parse_resource)
        else:
            parse_res_list(video_list, rename, parse_resource)

def start(url, config, cookies=None):
    """调用接口函数"""

    # 初始化设置
    global WORK_DIR
    CONFIG.update(config)

    # 课程信息
    course_info = get_summary(url)

    # 创建课程目录
    WORK_DIR = WorkingDir(CONFIG['dir'], course_info[1])

    WORK_DIR.change('Videos')
    FILES['renamer'] = Renamer(WORK_DIR.file('Rename.bat'))
    FILES['video'] = ClassicFile(WORK_DIR.file('Videos.txt'))

    # 获得资源
    get_resource(course_info[0])
