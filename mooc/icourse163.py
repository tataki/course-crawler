# -*- coding: utf-8 -*-
"""中国大学MOOC"""

import time
from .utils import *

CANDY = Crawler()
CONFIG = {}
FILES = {}


def get_summary(url):
    """从课程主页面获取信息"""

    url = url.replace('learn/', 'course/')
    res = CANDY.get(url).text

    term_id = re.search(r'termId : "(\d+)"', res).group(1)
    names = re.findall(r'name:"(.+)"', res)

    dir_name = course_dir(names[0], names[1])

    print(dir_name)
    CONFIG['term_id'] = term_id
    return term_id, dir_name


def parse_resource(resource):
    """解析资源地址和下载资源"""

    post_data = {'callCount': '1', 'scriptSessionId': '${scriptSessionId}190',
                 'httpSessionId': '5531d06316b34b9486a6891710115ebc', 'c0-scriptName': 'CourseBean',
                 'c0-methodName': 'getLessonUnitLearnVo', 'c0-id': '0', 'c0-param0': 'number:' + resource.meta[0],
                 'c0-param1': 'number:' + resource.meta[1], 'c0-param2': 'number:0',
                 'c0-param3': 'number:' + resource.meta[2], 'batchId': str(int(time.time() * 1000))}
    res = CANDY.post('https://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitLearnVo.dwr',
                     data=post_data).text

    file_name = resource.file_name
    if resource.type == 'Video':
        if CONFIG['hasToken']:
            video_token = CANDY.post('https://www.icourse163.org/web/j/resourceRpcBean.getVideoToken.rpc?csrfKey='+CONFIG['token'], data ={
                'videoId': resource.meta[0],
                'targetId': CONFIG['term_id'],
                'targetType': '0',
                }).json()['result']['signature']
            data = CANDY.post('https://vod.study.163.com/eds/api/v1/vod/video', data={
                'videoId': resource.meta[0],
                'signature': video_token,
                'clientType': '1'
            }).json()

            resolutions = [3, 2, 1]

            find = False
            for sp in resolutions[CONFIG['resolution']:]:
                # TODO: 增加视频格式选择
                for video in data['result']['videos']:
                    if video['quality'] == sp and video['format'] == 'mp4':
                        url = video['videoUrl']
                        ext = '.mp4'
                        find = True
                        break
                if find:
                    break
            res_print(file_name + ext)
            FILES['renamer'].write(re.search(r'(\w+\.mp4)', url).group(1), file_name, ext)
            FILES['video'].write_string(url)
            resource.ext = ext
        
        else:
            resolutions = ['Shd', 'Hd', 'Sd']
            for sp in resolutions[CONFIG['resolution']:]:
                # TODO: 增加视频格式选择
                # video_info = re.search(r'%sUrl="(?P<url>.*?(?P<ext>\.((m3u8)|(mp4)|(flv))).*?)"' % sp, res)
                video_info = re.search(r'(?P<ext>mp4)%sUrl="(?P<url>.*?\.(?P=ext).*?)"' % sp, res)
                if video_info:
                    url, ext = video_info.group('url', 'ext')
                    ext = '.' + ext
                    break
            res_print(file_name + ext)
            FILES['renamer'].write(re.search(r'(\w+\.((m3u8)|(mp4)|(flv)))', url).group(1), file_name, ext)
            FILES['video'].write_string(url)
            resource.ext = ext
        

        if not CONFIG['sub']:
            return
        subtitles = re.findall(r'name="(.+)";.*url="(.*?)"', res)
        WORK_DIR.change('Videos')
        for subtitle in subtitles:
            if len(subtitles) == 1:
                sub_name = file_name + '.srt'
            else:
                subtitle_lang = subtitle[0].encode('utf_8').decode('unicode_escape')
                sub_name = file_name + '_' + subtitle_lang + '.srt'
            res_print(sub_name)
            CANDY.download_bin(subtitle[1], WORK_DIR.file(sub_name))

    elif resource.type == 'Document':
        if WORK_DIR.exist(file_name + '.pdf'):
            return
        pdf_url = re.search(r'textOrigUrl:"(.*?)"', res).group(1)
        res_print(file_name + '.pdf')
        CANDY.download_bin(pdf_url, WORK_DIR.file(file_name + '.pdf'))

    elif resource.type == 'Rich':
        if WORK_DIR.exist(file_name + '.html'):
            return
        text = re.search(r'htmlContent:"(.*)",id', res.encode('utf_8').decode('unicode_escape'), re.S).group(1)
        res_print(file_name + '.html')
        with open(WORK_DIR.file(file_name + '.html'), 'w', encoding='utf_8') as file:
            file.write(text)


def get_resource(term_id):
    """获取各种资源"""

    outline = Outline()
    counter = Counter()

    video_list = []
    pdf_list = []
    rich_text_list = []

    post_data = {'callCount': '1', 'scriptSessionId': '${scriptSessionId}190', 'c0-scriptName': 'CourseBean',
                 'c0-methodName': 'getMocTermDto', 'c0-id': '0', 'c0-param0': 'number:' + term_id,
                 'c0-param1': 'number:0', 'c0-param2': 'boolean:true', 'batchId': str(int(time.time() * 1000))}
    res = CANDY.post('https://www.icourse163.org/dwr/call/plaincall/CourseBean.getMocTermDto.dwr',
                     data=post_data).text.encode('utf_8').decode('unicode_escape')

    chapters = re.findall(r'homeworks=\w+;.+id=(\d+).+name="([\s\S]+?)";', res)
    for chapter in chapters:
        counter.add(0)
        outline.write(chapter[1], counter, 0)

        lessons = re.findall(r'chapterId=' + chapter[0] + r'.+contentId=null.+contentType=1.+id=(\d+).+name="([\s\S]+?)"', res)
        for lesson in lessons:
            counter.add(1)
            outline.write(lesson[1], counter, 1)

            videos = re.findall(r'contentId=(\d+).+contentType=(1).+id=(\d+).+lessonId=' +
                                lesson[0] + r'.+name="([\s\S]+?)"', res)
            for video in videos:
                counter.add(2)
                outline.write(video[3], counter, 2, sign='#')
                video_list.append(Video(counter, video[3], video))
            counter.reset()

            pdfs = re.findall(r'contentId=(\d+).+contentType=(3).+id=(\d+).+lessonId=' +
                              lesson[0] + r'.+name="([\s\S]+?)"', res)
            for pdf in pdfs:
                counter.add(2)
                outline.write(pdf[3], counter, 2, sign='*')
                if CONFIG['doc']:
                    pdf_list.append(Document(counter, pdf[3], pdf))
            counter.reset()

            rich_text = re.findall(r'contentId=(\d+).+contentType=(4).+id=(\d+).+jsonContent=(.+?";);.+lessonId=' +
                                   lesson[0] + r'.+name="([\s\S]+?)"', res)
            for text in rich_text:
                counter.add(2)
                outline.write(text[4], counter, 2, sign='+')
                if CONFIG['text']:
                    rich_text_list.append(RichText(counter, text[4], text))
                if CONFIG['file']:
                    if text[3] != 'null' and text[3] != '""':
                        params = {'nosKey': re.search('nosKey":"(.+?)"', text[3]).group(1),
                                  'fileName': re.search('"fileName":"(.+?)"', text[3]).group(1)}
                        file_name = Resource.file_to_save(params['fileName'])
                        outline.write(file_name, counter, 2, sign='!')

                        WORK_DIR.change('Files')
                        res_print(params['fileName'])
                        file_name = '%s %s' % (counter, file_name)
                        CANDY.download_bin('https://www.icourse163.org/course/attachment.htm',
                                           WORK_DIR.file(file_name), params=params)
            counter.reset()

    if video_list:
        rename = WORK_DIR.file('Names.txt') if CONFIG['rename'] else False
        WORK_DIR.change('Videos')
        if CONFIG['dpl']:
            playlist = Playlist()
            parse_res_list(video_list, rename, parse_resource, playlist.write)
        else:
            parse_res_list(video_list, rename, parse_resource)
    if pdf_list:
        WORK_DIR.change('PDFs')
        parse_res_list(pdf_list, None, parse_resource)
    if rich_text_list:
        WORK_DIR.change('Texts')
        parse_res_list(rich_text_list, None, parse_resource)


def start(url, config, cookies):
    """调用接口函数"""

    global WORK_DIR
    CANDY.set_cookies(cookies)
    CONFIG.update(config)
    if cookies.get('NTESSTUDYSI'):
        CONFIG['hasToken'] = True
        CONFIG['token'] = cookies.get('NTESSTUDYSI')
    else:
        CONFIG['hasToken'] = False
    course_info = get_summary(url)

    WORK_DIR = WorkingDir(CONFIG['dir'], course_info[1])
    WORK_DIR.change('Videos')
    FILES['renamer'] = Renamer(WORK_DIR.file('Rename.bat'))
    FILES['video'] = ClassicFile(WORK_DIR.file('Videos.txt'))

    get_resource(course_info[0])

    if CONFIG['aria2']:
        del FILES['video']
        WORK_DIR.change('Videos')
        aria2_download(CONFIG['aria2'], WORK_DIR.path, webui=CONFIG['aria2-webui'], session=CONFIG['aria2-session'])
