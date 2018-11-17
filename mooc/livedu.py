# -*- coding: utf-8 -*-
"""北京高校优质课程研究会"""

import time
from .utils import *
from bs4 import BeautifulSoup


CANDY = Crawler()
CONFIG = {}
FILES = {}

def get_summary(url):
    """从课程主页面获取信息"""

    course_id = re.search(r'kcid=(?P<course_id>\d+)', url).group('course_id')
    data = {
        'kcid': course_id,
        'kcdm': course_id,
        }
    res = CANDY.post(CONFIG['study_page'], data=data)
    study_soup = BeautifulSoup(res.text, 'html.parser')
    name = study_soup.find('dl', class_='content-a-title').find('dt').find('span').string
    home_text = CANDY.get(url).text
    home_soup = BeautifulSoup(home_text, 'html.parser')
    chapter_names = []
    for chapter_lable in home_soup.find('div', class_='vice-main-kcap')\
        .find('ul')\
        .children:
        try:
            chapter_names.insert(0, chapter_lable.find('div').find('span').string)
        except:
            pass
    
    dir_name = course_dir(name, '北京高校优质课程研究会')

    print(dir_name)

    CONFIG['course_id'] = course_id
    CONFIG['study_soup'] = study_soup
    CONFIG['chapter_names'] = chapter_names
    return course_id, dir_name


def parse_resource(resource):
    """解析资源地址和下载资源"""

    file_name = resource.file_name
    if resource.type == 'Video':
        ext = '.mp4'
        res_print(file_name + ext)
        resource.ext = ext
        FILES['renamer'].write(re.search(r'(\w+\.mp4)', resource.meta).group(1), file_name, ext)
        FILES['video'].write_string(resource.meta)

    elif resource.type == 'Document':
        if WORK_DIR.exist(file_name + '.pdf'):
            return
        res_print(file_name + '.pdf')
        CANDY.download_bin(resource.meta, WORK_DIR.file(file_name + '.pdf'))

    elif resource.type == 'Rich':
        if WORK_DIR.exist(file_name + '.html'):
            return
        res_print(file_name + '.html')
        with open(WORK_DIR.file(file_name + '.html'), 'w', encoding='utf_8') as file:
            file.write(resource.meta)


def get_resource(course_id):
    """获取各种资源"""

    outline = Outline()
    counter = Counter()

    video_list = []
    pdf_list = []
    test_list = []

    study_soup = CONFIG['study_soup']
    chapter_names = CONFIG['chapter_names']
    study_div = study_soup.find('div', class_='ation-a-main')
    left_div = study_div.find('div', class_='xx-main-left')
    info_div = left_div.find('div', class_ = 'xx-left-main')
    chapters = info_div.find_all('dl')
    for chapter in chapters:
        counter.add(0)
        # chapter_name = chapter.find('dt').contents[2].strip()
        chapter_name = chapter_names.pop()
        outline.write(chapter_name, counter, 0)

        lessons = chapter.find_all('dd')
        for lesson in lessons:
            counter.add(1)
            lesson_info = lesson.find('a')
            lesson_id = re.search(r"xsxx\('(?P<lesson_id>.+)'\)", lesson_info.attrs.get('onclick')).group('lesson_id')

            data = {
                'kcdm': course_id,
                'zjdm': lesson_id,
                }
            res = CANDY.post(CONFIG['study_page'], data = data)
            soup=BeautifulSoup(res.text,'html.parser')
            study_div = soup.find('div', class_='ation-a-main')
            right_div = study_div.find('div', class_='xx-main-right')
            study_box = right_div.find('div', class_='xx-main-box')
            lesson_name = study_box.find('h4').contents[1]
            outline.write(lesson_name, counter, 1)
            resource_div = study_box.find('div', class_='study-L-text')

            # GET video url
            video_div = resource_div.find('div', id = 'videoBj_1')
            if video_div:
                video_info = video_div.a.attrs.get('onclick')
                video_params = list(map(lambda x:x.strip("'"),
                                        re.search(r'javascript:pauseVid\((?P<params>.+)\)', video_info).group('params').split(',')))
                video_name = f'Video:{lesson_name}'
                video_url = f'http://video.livedu.com.cn/{video_params[1]}?{video_params[0]}'
                outline.write(video_name, counter, 2, sign='#')
                video_list.append(Video(counter, video_name, video_url))
            
            # GET pdf url
            pdf_iframe = resource_div.find('iframe', attrs={'name':'pdfContainer'})
            if pdf_iframe:
                pdf_div = pdf_iframe.parent
                pdf_name = pdf_div.find('span').string.replace('.pdf', '')
                pdf_url = re.search(r'cclj=(?P<pdf_url>http.+\.pdf)', pdf_iframe.attrs.get('src')).group('pdf_url')
                outline.write(pdf_name, counter, 2, sign='*')
                if CONFIG['doc']:
                    pdf_list.append(Document(counter, pdf_name, pdf_url))
            
            # GET test text
            test_div = study_box.find('div', class_='zy-a-list')
            if test_div:
                test_name = f'Test:{lesson_name}'
                outline.write(test_name, counter, 2, sign='+')
                if CONFIG['text']:
                    test_list.append(RichText(counter, test_name, str(test_div)))

    if video_list:
        rename = WORK_DIR.file('Names.txt') if CONFIG['rename'] else False
        WORK_DIR.change('Videos')
        if CONFIG['dpl']:
            playlist = Playlist()
            parse_res_list(video_list, rename, playlist.write, parse_resource)
        else:
            parse_res_list(video_list, rename, parse_resource)
    if pdf_list:
        WORK_DIR.change('PDFs')
        parse_res_list(pdf_list, None, parse_resource)
    if test_list:
        WORK_DIR.change('Texts')
        parse_res_list(test_list, None, parse_resource)

def start(url, config, cookies=None):
    """调用接口函数"""

    # 初始化设置
    global WORK_DIR
    CANDY.set_cookies(cookies)
    CONFIG.update(config)
    CONFIG['study_page'] = 'http://www.livedu.com.cn/ispace4.0/moocxsxx/queryAllZjByKcdm.do'

    # 课程信息
    course_info = get_summary(url)

    # 创建课程目录
    WORK_DIR = WorkingDir(CONFIG['dir'], course_info[1])

    WORK_DIR.change('Videos')
    FILES['renamer'] = Renamer(WORK_DIR.file('Rename.bat'))
    FILES['video'] = ClassicFile(WORK_DIR.file('Videos.txt'))

    # 获得资源
    get_resource(course_info[0])

    if CONFIG['aria2']:
        del FILES['video']
        WORK_DIR.change('Videos')
        aria2_download(CONFIG['aria2'], WORK_DIR.path, webui=CONFIG['aria2-webui'], session=CONFIG['aria2-session'])
