# -*- coding: utf=8 -*-

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep
import re
import sys
import threading
import pyautogui
import logging
import hashlib

# 设置日志：同时输出到文件和控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("learn.log"),  # 输出到当前目录下的 log 文件
        logging.StreamHandler()               # 同时输出到控制台，方便实时查看
    ]
)

TIMEOUT_SEC = 10
WAIT_LONGER_SEC = 30  # 尝试延长等待时间解决测试出现慢问题

courses_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/commendIndex'  # 课程
subjects_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/projectIndex'  # 专题
specials_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/specialReList'  # 专栏


# 登陆
def login():
    login_url = 'https://sso.dtdjzx.gov.cn/sso/login'
    redirect_url = 'https://gbwlxy.dtdjzx.gov.cn/oauth2/login/pro'

    driver.get(login_url)
    logging.info('等待登录(300秒)')

    # TODO: 此元素可能不出现，有可能登陆后出个半页。看情况改成等待其他东西
    WebDriverWait(driver, 300).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, f'a[href="{redirect_url}"]')))
    # 经跳转页面进入index主页
    driver.get(redirect_url)

    logging.info('已登录')


finished_hours = 0.0
target_hours = 0.0

# 页面获取当前学时信息


def get_credit_hours():
    global finished_hours
    global target_hours

    personal_center_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/personalCenter'
    driver.get(personal_center_url)

    # 解决抓取过快获取总学时为0的问题
    target_hours = 0
    while not target_hours:
        sleep(.1)
        # 获取总学时
        target_hours = WebDriverWait(driver, TIMEOUT_SEC).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.plan-pro"))
        ).text
        # 获取已完成学时
        finished_hours = WebDriverWait(driver, TIMEOUT_SEC).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.plan-all-y"))
        ).text
        
    # 整理输出
    target_hours = float(re.findall(r'(\d+(\.\d+)?)', target_hours)[0][0])
    finished_hours = float(re.findall(r'(\d+(\.\d+)?)', finished_hours)[0][0])

    logging.info(f'当前进度（精确）：{finished_hours}/{target_hours}学时')


# 每次学完一课，计算学时
def update_credit_hours(course_info):
    global finished_hours
    global target_hours

    finished_hours += float(course_info[3])
    logging.info(f'当前进度（估计）：{finished_hours}/{target_hours}学时')
    if finished_hours >= target_hours:
        logging.info('学时可能已完成，将打开个人中心确认精确进度')
        get_credit_hours()
        if finished_hours >= target_hours:
            logging.info('学时已完成，程序退出')
            sys.exit(0)
        else:
            logging.info('学时未完成，继续学习')


def get_course_to_learn():
    global page_to_learn

    driver.get(courses_url)

    logging.info('搜索当前页面未完成课程')
    
    # 观察发现课程列表可能延迟数秒，或不出现，手动点击“全部”
    WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
        (By.XPATH, "//span[@class='el-tree-node__label' and text()='全部']"))).click()
    
    while True:
        # 等待向右翻页箭头出现
        next_button = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'i[class="el-icon el-icon-arrow-right"]')))

        sleep(.1)
        
        # 获取（等待）当前页面课程
        course_elems = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_all_elements_located(
            (By.CSS_SELECTOR, 'div[class="video-warp-start"]')))

        for course_elem in course_elems:
            # 提取当前课程元素信息
            # course_info: ['7341次', 'XX解读', '学习中', '授课教师：张三', '评分：9.7', '时长：', '42:00', '学时：', '1']
            course_info = course_elem.text.split('\n')
            _, course_name, course_progress, _, _, _, course_duration, _, course_credit_hours = course_info

            # 如果找到未学课程，则return，进入学习
            if course_progress != '已学习':
                page_to_learn = course_elem
                info = [course_name, course_progress,
                        course_duration, course_credit_hours]
                if course_progress == '未通过考试':
                    logging.info(f'准备 {course_name} 测试')
                    return info, False  # 是否需要视频学习
                else:
                    logging.info(
                        f'准备学习 {course_name}，时长{course_duration}，学时{course_credit_hours}')
                    return info, True  # 是否需要视频学习

        # for循环运行结束，表明当前页面所有课程已学习，点击 “>” 下一页
        logging.info('当前页面所有课程已学习，进入下一页搜索')
        next_button.click()

# sub_idx_to_learn：在“正在举办”页中学习第几个专题（0，1，2。。。） # TODO 翻页


def to_subject(sub_idx_to_learn=None):
    sleep(1)
    driver.get(subjects_url)  # 进入 专题 页面

    # WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
    #     (By.XPATH, '//p[text()="正在举办"]'))).click()  # 确保进入 正在举办 tab
    # 似乎默认进入此tab，不需点击？

    # cur_tab_elem = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[class="content-tab active-content"]'))) # 获取此tab下内容
    sleep(1)
    subjects = WebDriverWait(driver, TIMEOUT_SEC).until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, 'div[class="course-list-item-message"]')))  # 获取课程信息
    # subjects = cur_tab_elem.find_elements(By.CSS_SELECTOR,'div[class="course-list-item-message"]') # 获取课程信息
    if sub_idx_to_learn is None:
        subjects_status = [s.find_elements(By.XPATH,
                                           'p')[1].text.split('\n')[-1] for s in subjects]  # 课程报名状态
        attended_idx = subjects_status.index('已报名')  # 学习 已报名
    else:
        attended_idx = sub_idx_to_learn
    subject_to_learn = subjects[attended_idx]

# sub_idx_to_learn：学习第几个（0，1，2。。。） # TODO 翻页


def to_special(sub_idx_to_learn=None):
    sleep(1)
    driver.get(specials_url)  # 进入 专栏 页面
    sleep(1)
    subjects = WebDriverWait(driver, TIMEOUT_SEC).until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, 'div[class="specialCard gestures"]')))  # 获取课程信息
    subject_to_learn = subjects[sub_idx_to_learn]


# subject_url用于处理无法打开专题页面的情况，直接进入专题网址
def get_subject_course_to_learn(subject_url=None):
    global page_to_learn
    sleep(.5)

    if subject_url is None:
        subject_to_learn.click()
        logging.info('调用get_subject_course_to_learn,未指定subject_url')
    else:
        driver.get(subject_url)
        logging.info('调用get_subject_course_to_learn,指定subject_url')

    sleep(2)
    next_button = WebDriverWait(driver, TIMEOUT_SEC).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[class="btn-next"]')))
    logging.info('获取‘下一页’按钮')

    is_compulsory = True  # 默认进入必修课程
    # while not next_button.is_enabled():
    sleep(.5)

    # 等待元素出现，解决 Unable to locate element 问题
    WebDriverWait(driver, TIMEOUT_SEC).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'li[class="number active"]')))
    sleep(.5)

    # page_cnt = len(driver.find_elements(By.CSS_SELECTOR,'li[class="number"]')) + 1 # 旧，疑似网页改结构已不适配
    page_cnt = int(driver.find_elements(
        By.CSS_SELECTOR, 'li[class="number"]')[-1].text)
    if page_cnt is None:  # 解决课程目录只有一页时css获取'li[class="number"]'为空问题
        page_cnt = 1
    cur_active = int(driver.find_element(
        By.CSS_SELECTOR, 'li[class="number active"]').text)

    while cur_active <= page_cnt:
        logging.info(f'当前课程页数：{cur_active}/{page_cnt}')
        sleep(1)
        courses = WebDriverWait(driver, TIMEOUT_SEC).until(EC.presence_of_all_elements_located(
            # (By.CSS_SELECTOR, 'div[class="course-list-item-message"]')))  # 获取所有学习状态按钮 （ 已学习 / 未学习 ） # 网站更新？
            # (By.CSS_SELECTOR, 'div[class="course-list-item-message active"]')))  # 获取所有学习状态按钮 （ 已学习 / 未学习 ）
            (By.CSS_SELECTOR, 'div[class="course-list-item"]')))  # 已学\未学课程CSS_SELECTOR似乎不同，使用上级selector
        valid_courses = [c for c in courses if c.text != '']
        # logging.info(len(valid_courses))
        for c in valid_courses:
            if c.text[-3:] != '已学习':
                page_to_learn = c.find_element(By.CSS_SELECTOR, 'h2')
                course_name = c.text.split('\n')[1]  # 获取课程名
                if c.text[-3:] == '过考试':
                    logging.info(f'准备 {course_name} 测试')
                    return False  # 是否需要视频学习
                else:
                    logging.info(f'准备学习 {course_name}')
                    return True  # 是否需要视频学习

        if is_compulsory and (not next_button.is_enabled()):  # 必修课程遍历完毕，进入选修课程
            driver.find_element(
                By.XPATH, '//p[text()="选修课程"]').click()
            is_compulsory = False
            assert next_button.is_enabled()
        logging.info('当前页面所有课程已学习，进入下一页搜索')
        next_button.click()
        sleep(.5)
        cur_active = int(driver.find_element(By.CSS_SELECTOR,
                                             'li[class="number active"]').text)


def get_special_course_to_learn():
    global page_to_learn
    sleep(.5)
    subject_to_learn.click()
    sleep(2)
    next_button = WebDriverWait(driver, TIMEOUT_SEC).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[class="btn-next"]')))
    sleep(.5)

    # 等待元素出现，解决 Unable to locate element 问题
    WebDriverWait(driver, TIMEOUT_SEC).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'li[class="number active"]')))
    sleep(.5)

    # page_cnt = len(driver.find_elements(By.CSS_SELECTOR,'li[class="number"]')) + 1 # 旧，疑似网页改结构已不适配
    page_cnt = int(driver.find_elements(
        By.CSS_SELECTOR, 'li[class="number"]')[-1].text)
    if page_cnt is None:  # 解决课程目录只有一页时css获取'li[class="number"]'为空问题
        page_cnt = 1
    cur_active = int(driver.find_element(
        By.CSS_SELECTOR, 'li[class="number active"]').text)

    while cur_active <= page_cnt:
        sleep(1)
        courses = WebDriverWait(driver, TIMEOUT_SEC).until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, 'div[class="class-card gestures "]')))  # 获取所有学习状态按钮 （ 已学习 / 未学习 ）
        valid_courses = [c for c in courses if c.text != '']
        # logging.info(len(valid_courses))
        for c in valid_courses:
            if c.text.split('\n')[2] != '已学习':
                page_to_learn = c.find_element(
                    By.CSS_SELECTOR, 'div[class="top-title"]')
                course_name = c.text.split('\n')[1]
                if c.text.split('\n')[2] == '未通过考试':
                    logging.info(f'准备 {course_name} 测试')
                    return False  # 是否需要视频学习
                else:
                    logging.info(f'准备学习 {course_name}')
                    return True  # 是否需要视频学习
        next_button.click()
        sleep(.5)
        cur_active = int(driver.find_element(By.CSS_SELECTOR,
                                             'li[class="number active"]').text)
        logging.info('当前页面所有课程已学习，进入下一页搜索')


def learn_course(course_info=None, watch_video=True, is_subject_course=False):
    global page_to_learn

    page_to_learn.click()  # 进入视频播放页
    WebDriverWait(driver, TIMEOUT_SEC).until(
        EC.new_window_is_opened)
    if is_subject_course:  # 专题课程会打开新窗口，进行跳转
        driver.switch_to.window(driver.window_handles[1])

    if not watch_video:  # 不需视频学习，则直接进行测试
        WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'img[class="rightBottom"]'))).click()  # 点击 随堂测试
        do_exam()
        update_credit_hours(course_info)
        return

    # 获取播放按钮（此时未显示时长）
    play_button = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, 'button[title="Play Video"]')))

    # 点击播放、暂停，用于显示时长
    play_button.click()
    sleep(.5)
    # WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located( # 好像不用暂停
    #     (By.CSS_SELECTOR, 'button[title="Pause"]'))).click()  # 暂停

    while True:
        # 获取总时长([hh]:mm:ss)
        total_duration_text = WebDriverWait(driver, TIMEOUT_SEC).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'span.vjs-duration-display'))).text
        if sum(int(i) for i in total_duration_text.split(':')):
            break
        sleep(.1)

    total_duration = [int(i) for i in total_duration_text.split(':')]

    if len(total_duration) == 3:
        total_dur_sec = total_duration[0] * 3600 + \
            total_duration[1] * 60 + total_duration[2]
    else:
        total_dur_sec = total_duration[0] * 60 + total_duration[1]

    played_dur_sec = 0

    # 距视频结束还有5秒以上时，循环获取播放时间
    while total_dur_sec-played_dur_sec > 5:
        sleep(1)
        # 播放时会隐藏时间，此句获取为空；通过运行javascript获取
        # played_duration_text = WebDriverWait(driver, TIMEOUT_SEC).until(
        #     EC.presence_of_element_located((By.CSS_SELECTOR, 'span.vjs-current-time-display'))).text
        played_duration_text = driver.execute_script(
            "return document.querySelector('span.vjs-current-time-display').innerText;")
        played_duration = [int(i) for i in played_duration_text.split(':')]
        if len(played_duration) == 3:
            played_dur_sec = played_duration[0] * 3600 + \
                played_duration[1] * 60 + played_duration[2]
        else:
            played_dur_sec = played_duration[0] * 60 + played_duration[1]
        print(
            f'\r视频播放中 {played_duration_text} / {total_duration_text}', end='', flush=True)

    # 判断是否有随堂测试
    # 如果有测试，不会出现播放回放按钮，播放完成后面直接跳转到测试
    while True:
        has_test = driver.find_element(
            By.CSS_SELECTOR, 'div.title-list').text.split('\n随堂测试：\n')[1][0]
        if has_test in ['是', '否']:
            break
        else:
            print(f'\r尝试获取测试信息：has_test->{has_test}', end='', flush=True)
        sleep(.2)
    
    
    logging.info('\n等待播放结束')
    
    if has_test == '是':
        sleep(5) # 确保视频播放完
        # 视频播放后可能自动跳转或不跳转，在do_exam里处理
        do_exam()
    else:
        # 通过回放按钮出现判断视频播放完成
        WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'button[title="Replay"]')))
    if is_subject_course:  # 关闭专题课程新窗口，跳转回原窗口
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    logging.info('此课程学习完成\n')
    update_credit_hours(course_info)

'''
2025-10-31发现题目、选项顺序会变！改为使用题干、题目选项的哈希
ans_dic[i] = [0, 0, 0]  # {题目ID：[类型，是否正确答案，当前选择答案(index)]} 
<--------------------- 原 ans_dic 结构
现ans_dic 结构 ---------------------> 单选、多选统一此结构
ans_dic = 
{
    h_1:{ 第一题题干文本哈希
        'type':0, 0:单选/判断； 1：多选
        o_1:1, 第一选项文本哈希:是否勾选
        o_2:0,
        o_3:0,
        ...
    },
    h_2:{...}，
    ...
}  
'''
def gen_hash(text):
    # 创建SHA-256哈希对象
    hash_object = hashlib.sha256(text.encode('utf-8'))
    # 返回十六进制格式的哈希值作为题目ID
    return hash_object.hexdigest()

def next_choice(dic):
    # 创建新字典，保留'type'键值对
    type = dic['type']
    new_dict = {'type': type}
    # 获取除'type'外的所有键（保持插入顺序）
    hash_keys = [k for k in dic.keys() if k != 'type']
    # 提取哈希键对应的值，组成二进制字符串
    bin_str = ''.join(dic[k] for k in hash_keys)
    
    if not type: # 单选/判断：对二进制字符串进行右移一位操作
        new_bin_str = '0' + bin_str[:-1]
    else: # 多选：
        new_bin_str = bin((int(bin_str, 2) -1))[2:].zfill(len(dic.keys())-1)

    # 将新的二进制值分配回对应的哈希键
    for i, key in enumerate(hash_keys):
        new_dict[key] = new_bin_str[i]
    return new_dict


def do_exam():
    logging.info('正在进入测试')
    
    while True: # 用于解决：某些课程可能需要手动点击进入测试；进入测试后可能页面空白
        if 'examManage' in driver.current_url:
            question_status = WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR,
                    'div[class="top_e"]'))
            )
            if question_status == '1/0':
                logging.error('出现测试页面空白，尝试重进')
                driver.back()
                continue
            break
        elif 'coursedetail' in driver.current_url:
            try:
                driver.find_element(By.CSS_SELECTOR, 'img.rightBottom').click() # "随堂测试 立即进入"
            except:
                sleep(.2)
                continue
            break
        else:
            logging.error(f'URL异常：{driver.current_url}')
            raise
    
    sleep(.2) # 等待，提升稳定性
    logging.info('已进入测试')
    

    # 获取进入测试页面后的“确定”按钮
    button = WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR,
             'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))
    )


    driver.execute_script("arguments[0].click();", button) # 使用 javascript 点击 确定

    

    question_num = int(driver.find_element(By.CSS_SELECTOR,
                                        'div[class="top_e"] div').text.split('/')[1])  # 题目数
    logging.info(f'进入测试，共 {question_num} 题')

    question_type_map = {
        '单选':0,
        '判断':0,
        '多选':1
    }

    ans_dic = {}  # 答案字典    
    while True:
        # 获取所有 下一题/交卷 按钮
        # 此处获取了所有 上一题 / 下一题 /交卷，筛选出偶数项
        next_n_submit_buttons = driver.find_elements(By.CSS_SELECTOR, 'div.bast_quest_btn')[1::2]

        all_questions = [] # 所有题目的题干、选项
        while not len(all_questions): # 等待题目完全显示
            sleep(.2)
            all_questions = WebDriverWait(driver, TIMEOUT_SEC).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR,
                        'div[class="examcontent"]'))
                )
        assert len(all_questions) == question_num
        
        current_stem_hashes = [] # 用于顺序存储此轮题目哈希

        # TODO:这里输出ans_dic看看！！！，似乎有死循环

        # 遍历处理每个题目
        for i, q in enumerate(all_questions): # 将all_questions的题干、选项做哈希，存到ans_dic里
            sleep(.2)
            # q文本："1. 单选 题干XXX \nA aaa \nB bbb ..."
            question_elem = q.find_elements(By.CSS_SELECTOR,'div') # 注意到 q包含两个div，其一是题干，其二是各选项
            
            # 获取类型、题干
            question_stem_text = question_elem[0].text.split('. ', maxsplit=1)[1] #题干，去掉题号
            question_type, question_stem_text = question_stem_text.split(' ', maxsplit=1) #去掉类型（单选多选判断）
            
            # 获取选项元素及文本
            question_opts_elems = question_elem[1].find_elements(By.CSS_SELECTOR, 'label')
            question_opts_texts = [opt_elem.text.split(' ', maxsplit=1)[1] for opt_elem in question_opts_elems]
            
            # 求哈希
            stem_hash = gen_hash(question_stem_text)
            opts_hash = list(map(gen_hash, question_opts_texts))

            current_stem_hashes.append(stem_hash)
            
            # ans_dic 初次写入信息
            if stem_hash not in ans_dic.keys():
                # 组 ans_dic
                type = question_type_map[question_type]
                opts_num = len(opts_hash) # 选项个数
                if type: # 多选：
                    target_opts = '1'*opts_num # 如：1111
                else:
                    target_opts = '1'+'0'*(opts_num-1) # 如：1000
                # 合并字典
                ans_dic[stem_hash] = {'type':type} | dict(zip(opts_hash, target_opts))

                '''
                得到：
                {'9db0ce813371d0d4a75ea95c6e55e77e07bdc9b0da79b2ca45142aefd379c043':
                    {
                    'type': 0,
                    '0f7a70afb531985b0718ed3f46bc40e7aa1650951a4dd783f2c708cb2de5669c': '1',
                    'b989d4997af33924612ce7165fa3a685e798f823b985b4ae388a76cc3803a950': '0',
                    'd18c75fe308263bbd57346698246a7bb568bd12555e792aa68d1bceaa7a317e6': '0',
                    'ac6879236e5c0fa112468b2b4edf3df8b0dc0f3189aacae7d7cb00c218cff10e': '0'}
                    }
                '''
            
            # 遍历每个选项 判断是否勾选
            for j, opt_elem in enumerate(question_opts_elems):
                toCheck = int(ans_dic[stem_hash][gen_hash(question_opts_texts[j])])
                if toCheck:
                    sleep(.2)
                    opt_elem.click()

            logging.info(f'next_n_submit_buttons[i].click()  # 点击 下一题（或交卷）{i}')
            assert next_n_submit_buttons[i].text != ''
            next_n_submit_buttons[i].click()  # 点击 下一题（或交卷）
            if i == question_num - 1:
                try: # 解决可能不点击 交卷 的问题
                    sleep(.5)
                    next_n_submit_buttons[i].click()
                except:
                    logging.info('已点击 交卷')
                
                WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'button[class="el-button el-button--default el-button--small el-button--primary "]'))).click()  # 交卷 确定

                result_info = WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'div[class="infoclass"]'))).text  # 获取测试结果
                
                if result_info.split('\n')[0][-3:] == '不合格':  # 测试不合格，回看试题
                    WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--default el-button--mini"]'))).click()
                    
                    # 获取错误题目
                    wrong_answers = WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(
                        EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'li[class="activess isred"]')))
                    wrong_answer_idx = [int(a.text)-1 for a in wrong_answers] # 错题 idx
                    for i in wrong_answer_idx: # 处理错题
                        # 某题做错，需把这题的答案 右移（单选） 或 减一（多选）
                        # 不必管选项顺序，选项是按哈希点的，此处只处理：“题错了，调整为下一选项” 就可以了
                        # 但需要对应到相应的题目上
                        ans_dic[current_stem_hashes[i]] = next_choice(ans_dic[current_stem_hashes[i]])

                    driver.find_element(By.CSS_SELECTOR,
                                        'button[class="el-button exit el-button--default el-button--mini"]').click()  # 退出回看
                    WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'img[class="rightBottom"]'))).click()  # 重新进入测试
                    WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))).click()  # 确定
                else:
                    WebDriverWait(driver, TIMEOUT_SEC + WAIT_LONGER_SEC).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button modelBtn exitBtn  el-button--primary el-button--mini"]'))).click()  # 通过测试，退出
                    logging.info('通过测试')
                    return

# 每5分移动一次鼠标，避免系统休眠或关机
def prevent_sleep():
    while True:
        # 移动鼠标一个像素并移回原位
        pyautogui.moveRel(1, 0, duration=0.1)  # 向右移动1个像素
        pyautogui.moveRel(-1, 0, duration=0.1)  # 然后移回到左边

        # 等待5分钟
        sleep(300)


# 创建防止睡眠的线程
prevent_sleep_thread = threading.Thread(target=prevent_sleep)
prevent_sleep_thread.daemon = True  # 设置为守护线程，这样主线程结束时它也会结束

# 启动防止睡眠的线程
prevent_sleep_thread.start()

subject_to_learn = None  # 避免专题、专栏函数报错用，函数未更新，有必要再改

# 处理SSL证书错误问题，忽略无用的日志
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--ignore-ssl-errors')
chrome_options.add_experimental_option(
    "excludeSwitches", ['enable-automation', 'enable-logging'])
# 网站默认静音
chrome_options.add_argument("--mute-audio")

# 打开浏览器
driver = webdriver.Chrome(options=chrome_options)

# 用于UOS，使用firefox时：
# from selenium.webdriver.firefox.service import Service
# # 指定geckodriver路径
# service = Service('path_to/dt_learn/geckodriver36')
# driver = webdriver.Firefox(service=service)

driver.maximize_window()  # 窗口最大化

# 以下页面操作
login()
get_credit_hours()

# ------------------------------------------------------



# 时间紧任务重，直接这么搞吧
if __name__ == "__main__":
    while True:
        try:
            info, course_status = get_course_to_learn()
            learn_course(course_info=info, watch_video=course_status)
        except KeyboardInterrupt:
            logging.info("手动中断")
            break
        except Exception as e:
            logging.error(f"错误: {e}")  # 记录错误日志
            sleep(10)
            continue
        logging.info('本轮成功执行')
        
    
# ------------------------------------------------------

# 学习课程
# while True:
#     info, course_status = get_course_to_learn()
#     learn_course(course_info=info, watch_video=course_status)

# 学习专题课程
# while True:
#     to_subject(6) # 跳转到“网上专题班”页面
#     course_status = get_subject_course_to_learn()
#     learn_course(watch_video=course_status, is_subject_course=True)

# 学习专题课程，用于“网上专题班”页面持续转圈无法打开时，直接输入网址进入对应专题学习
# subject_url='https://gbwlxy.dtdjzx.gov.cn/content#/projectDetail?id=3646720435925550517'
# while True:
#     course_status = get_subject_course_to_learn(subject_url)
#     learn_course(watch_video=course_status, is_subject_course=True)
#     driver.refresh() # 解决学完课程后仍显示未学问题

# 学习专栏课程
# while True:
#     to_special(1)  # 跳转到“网上专题班”页面
#     course_status = get_special_course_to_learn()
#     learn_course(watch_video=course_status, is_subject_course=False)
