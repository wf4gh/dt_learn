# -*- coding: utf=8 -*-

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep
import re

TIMEOUT_SEC = 10


courses_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/commendIndex'  # 课程
subjects_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/projectIndex'  # 专题
specials_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/specialReList'  # 专栏


# 登陆
def login():
    login_url = 'https://sso.dtdjzx.gov.cn/sso/login'
    redirect_url = 'https://gbwlxy.dtdjzx.gov.cn/oauth2/login/pro'

    driver.get(login_url)
    print('等待登录(300秒)')
    WebDriverWait(driver, 300).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, f'a[href="{redirect_url}"]')))
    # 经跳转页面进入index主页
    driver.get(redirect_url)

    print('已登录')


# 获取当前学时信息
def get_credit_hours():
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
    finished_hours = re.findall(r'\d+', finished_hours)[0]
    target_hours = re.findall(r'\d+', target_hours)[0]
    print(f'当前进度：{finished_hours}/{target_hours}学时')

    return int(finished_hours), int(target_hours)


# 进入【课程推荐】，并跳转至第target_page_num页
# def to_course_page(target_page_num=1):
#     driver.get(courses_url)
#     current_page = 1

#     while current_page < target_page_num:
#         # 观察发现课程列表可能延迟数秒，但会和页码及翻页键同时出现
#         # 此处等待向右翻页箭头出现
#         WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
#             (By.CSS_SELECTOR, 'i[class="el-icon el-icon-arrow-right"]'))).click()
#         current_page = int(WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
#             (By.CSS_SELECTOR, 'li[class="number active"]'))).text)  # 获取新的当前页码


def get_course_to_learn():
    global page_to_learn

    driver.get(courses_url)
    # to_course_page(1)

    print('搜索当前页面未完成课程')
    while True:
        # 观察发现课程列表可能延迟数秒，但会和页码及翻页键同时出现
        # 此处等待向右翻页箭头出现
        next_button = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'i[class="el-icon el-icon-arrow-right"]')))

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
                    print(f'准备 {course_name} 测试')
                    return info, False  # 是否需要视频学习
                else:
                    print(
                        f'准备学习 {course_name}，时长{course_duration}，学时{course_credit_hours}')
                    return info, True  # 是否需要视频学习

        # for循环运行结束，表明当前页面所有课程已学习，点击 “>” 下一页
        print('当前页面所有课程已学习，进入下一页搜索')
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
        print('调用get_subject_course_to_learn,未指定subject_url')
    else:
        driver.get(subject_url)
        print('调用get_subject_course_to_learn,指定subject_url')

    sleep(2)
    next_button = WebDriverWait(driver, TIMEOUT_SEC).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[class="btn-next"]')))
    print('获取‘下一页’按钮')

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
        print(f'当前课程页数：{cur_active}/{page_cnt}')
        sleep(1)
        courses = WebDriverWait(driver, TIMEOUT_SEC).until(EC.presence_of_all_elements_located(
            # (By.CSS_SELECTOR, 'div[class="course-list-item-message"]')))  # 获取所有学习状态按钮 （ 已学习 / 未学习 ） # 网站更新？
            # (By.CSS_SELECTOR, 'div[class="course-list-item-message active"]')))  # 获取所有学习状态按钮 （ 已学习 / 未学习 ）
            (By.CSS_SELECTOR, 'div[class="course-list-item"]')))  # 已学\未学课程CSS_SELECTOR似乎不同，使用上级selector
        valid_courses = [c for c in courses if c.text != '']
        # print(len(valid_courses))
        for c in valid_courses:
            if c.text[-3:] != '已学习':
                page_to_learn = c.find_element(By.CSS_SELECTOR, 'h2')
                course_name = c.text.split('\n')[1]  # 获取课程名
                if c.text[-3:] == '过考试':
                    print(f'准备 {course_name} 测试')
                    return False  # 是否需要视频学习
                else:
                    print(f'准备学习 {course_name}')
                    return True  # 是否需要视频学习

        if is_compulsory and (not next_button.is_enabled()):  # 必修课程遍历完毕，进入选修课程
            driver.find_element(
                By.XPATH, '//p[text()="选修课程"]').click()
            is_compulsory = False
            assert next_button.is_enabled()
        print('当前页面所有课程已学习，进入下一页搜索')
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
        # print(len(valid_courses))
        for c in valid_courses:
            if c.text.split('\n')[2] != '已学习':
                page_to_learn = c.find_element(
                    By.CSS_SELECTOR, 'div[class="top-title"]')
                course_name = c.text.split('\n')[1]
                if c.text.split('\n')[2] == '未通过考试':
                    print(f'准备 {course_name} 测试')
                    return False  # 是否需要视频学习
                else:
                    print(f'准备学习 {course_name}')
                    return True  # 是否需要视频学习
        next_button.click()
        sleep(.5)
        cur_active = int(driver.find_element(By.CSS_SELECTOR,
                                             'li[class="number active"]').text)
        print('当前页面所有课程已学习，进入下一页搜索')


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
    while total_dur_sec-played_dur_sec > 3:
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
        print(f'\r{played_duration_text} / {total_duration_text}', end='', flush=True)

    # todo: 重写此处逻辑

    # # 获取视频长度
    # dur = 5
    # while dur == 5:  # 解决获取0：00问题
    #     sleep(.5)
    #     splited_dur = driver.find_element(By.CSS_SELECTOR,
    #                                       'span.vjs-duration-display').text.split(':')
    #     if len(splited_dur) == 2:  # 处理视频时长超过一小时问题
    #         mins, secs = splited_dur
    #         hours = '0'
    #     else:
    #         assert len(splited_dur) == 3
    #         hours, mins, secs = splited_dur
    #     if hours.isdigit() and mins.isdigit() and secs.isdigit():  # 解决获取 mins:secs 为 -:- 问题
    #         dur = int(hours) * 3600 + int(mins) * 60 + int(secs) + 5

    # print(f'视频长度 {hours}:{mins}:{secs} ，随堂测试: {"有" if has_test else "无"} ，开始学习')
    # sleep(2)  # 0.5 -> 2秒，尝试解决 not interactable 问题
    # play_button = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
    #     (By.CSS_SELECTOR, 'button[title="Play Video"]')))  # 重新获取 play_button，尝试解决 not interactable 问题
    # sleep(.5)
    # play_button.click()

    # sleep(dur)

    
    # 判断是否有随堂测试
    # 如果有测试，不会出现播放回放按钮，播放完成后面直接跳转到测试
    has_test = driver.find_element(
        By.CSS_SELECTOR, 'div.title-list').text.split('\n')[-3]
    assert has_test in ['是', '否']  # 不满足，则需要改动上面语句
    if has_test == '是':
        print('等待进行测试')
        do_exam()
    else:
        # 通过回放按钮出现判断视频播放完成
        print('等待播放结束')
        WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'button[title="Replay"]')))
        print('播放结束')
        
    # has_test = driver.find_element(By.CSS_SELECTOR,
    #                                'div.title-list').text == '是'
    # if has_test:
    #     do_exam()
    # else:
    #     WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
    #         (By.CSS_SELECTOR, 'button[title="Replay"]')))

    if is_subject_course:  # 关闭专题课程新窗口，跳转回原窗口
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    print('此课程学习完成\n')


def do_exam():
    wait_longer_sec = 30  # 尝试延长等待时间解决测试出现慢问题
    # sleep(10)  # 尝试延长等待时间解决测试出现慢问题
    WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))).click()  # 随堂测试 确定
    print('进入测试')
    ans_dic = {}  # 答案字典
    all_trials = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, 'div[class="scroll_content"]')))  # 获取所有题目 题干、选项、按钮
    next_buttons = all_trials.find_elements(By.XPATH,
                                            '//div[text()="下一题"]')  # 获取所有 下一题/交卷 按钮
    trial_num = int(driver.find_element(By.CSS_SELECTOR,
                                        'div[class="top_e"] div').text.split('/')[1])  # 题目数
    print(f'测试共有 {trial_num} 道题')

    all_trial_options = driver.find_elements(By.CSS_SELECTOR,
                                             'div[class="options_wraper"]')  # 获取所有题目选项组
    while True:
        for i in range(trial_num):
            options = all_trial_options[i]  # 当前题目选项组
            opt_elems = options.find_elements(By.CSS_SELECTOR,
                                              'label')  # 当前题目选项
            opt_counts = len(opt_elems)  # 当前题目选项数

            if i not in ans_dic.keys():  # 第一轮答题
                cur_type = ''.join([t.text for t in driver.find_elements(By.CSS_SELECTOR,
                                                                         'span[class="quest_tyle"]')])  # 当前题目类型 单选: 0 / 多选: 1
                if cur_type in ['单选', '判断']:
                    ans_dic[i] = [0, 0, 0]  # 类型，是否正确答案，当前选择答案(index)
                    opt_elems[ans_dic[i][2]].click()
                else:
                    assert cur_type == '多选'
                    # 类型，是否正确答案，当前选择答案（例：1111 表示全选）
                    ans_dic[i] = [1, 0, '1' * opt_counts]
                    for j, o in enumerate(ans_dic[i][2]):
                        if int(o):
                            opt_elems[j].click()
            else:  # 非第一轮答题
                if ans_dic[i][1]:  # 上一轮答案正确
                    if ans_dic[i][0]:  # 多选
                        for j, o in enumerate(ans_dic[i][2]):
                            if int(o):
                                opt_elems[j].click()
                    else:  # 单选
                        opt_elems[ans_dic[i][2]].click()
                else:  # 上一轮答案错误
                    if ans_dic[i][0]:  # 多选
                        ans_dic[i][2] = bin(
                            int(ans_dic[i][2], 2) - 1)[2:].zfill(opt_counts)
                        for j, o in enumerate(ans_dic[i][2]):
                            if int(o):
                                sleep(.1)
                                opt_elems[j].click()
                    else:  # 单选
                        ans_dic[i][2] += 1
                        sleep(.1)
                        opt_elems[ans_dic[i][2]].click()
            sleep(.5)
            next_buttons[i].click()  # 点击 下一题（或交卷）
            if i == trial_num - 1:
                WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'button[class="el-button el-button--default el-button--small el-button--primary "]'))).click()  # 交卷 确定

                result_info = WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'div[class="infoclass"]'))).text  # 获取测试结果

                print('已交卷，正在核对答案')

                if result_info.split('\n')[0][-3:] == '不合格':  # 测试不合格
                    print('测试未通过')
                    WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--default el-button--mini"]'))).click()  # 回看试题
                    correct_answers = WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(
                        EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'li[class="activess"]')))
                    correct_idx = [
                        int(ca.text) - 1 for ca in correct_answers]
                    for idx in correct_idx:
                        ans_dic[idx][1] = 1
                    driver.find_element(By.CSS_SELECTOR,
                                        'button[class="el-button exit el-button--default el-button--mini"]').click()  # 退出回看
                    WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'img[class="rightBottom"]'))).click()  # 重新进入测试
                    WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))).click()  # 确定
                    print('答案已记录，再次进行测试')

                    all_trials = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'div[class="scroll_content"]')))  # 重新获取所有题目 题干、选项、按钮
                    next_buttons = all_trials.find_elements(By.XPATH,
                                                            '//div[text()="下一题"]')  # 重新获取所有 下一题/交卷 按钮
                    all_trial_options = driver.find_elements(By.CSS_SELECTOR,
                                                             'div[class="options_wraper"]')  # 获取所有题目选项组

                else:
                    WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button modelBtn exitBtn  el-button--primary el-button--mini"]'))).click()  # 通过测试，退出
                    print('通过测试')
                    return


# 处理SSL证书错误问题，忽略无用的日志
my_options = webdriver.ChromeOptions()
my_options.add_argument('--ignore-certificate-errors')
my_options.add_argument('--ignore-ssl-errors')
my_options.add_experimental_option(
    "excludeSwitches", ['enable-automation', 'enable-logging'])

# 打开浏览器
driver = webdriver.Chrome(options=my_options)
driver.maximize_window()  # 窗口最大化

# 以下页面操作
login()
get_credit_hours()

subject_to_learn = None  # 要学习的专题
page_to_learn = None  # 要学习的具体课程（专题或课程中）

info, course_status = get_course_to_learn()
learn_course(course_info=info, watch_video=course_status)

def test():
    for i in range(5, 0, -1):
        print(f'\r{i}/{i+1}', end='', flush=True)
        sleep(1)

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
