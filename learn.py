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

    print(f'当前进度（精确）：{finished_hours}/{target_hours}学时')


# 每次学完一课，计算学时
def update_credit_hours(course_info):
    global finished_hours
    global target_hours

    finished_hours += float(course_info[3])
    print(f'当前进度（估计）：{finished_hours}/{target_hours}学时')
    if finished_hours >= target_hours:
        print('学时可能已完成，将打开个人中心确认精确进度')
        get_credit_hours()
        if finished_hours >= target_hours:
            print('学时已完成，程序退出')
            sys.exit(0)
        else:
            print('学时未完成，继续学习')


def get_course_to_learn():
    global page_to_learn

    driver.get(courses_url)

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
    if has_test == '是':
        print('\n等待进行测试')
        do_exam()
    else:
        # 通过回放按钮出现判断视频播放完成
        print('\n等待播放结束')
        WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'button[title="Replay"]')))
        print('播放结束')

    if is_subject_course:  # 关闭专题课程新窗口，跳转回原窗口
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    print('此课程学习完成\n')
    update_credit_hours(course_info)


def do_exam():
    wait_longer_sec = 30  # 尝试延长等待时间解决测试出现慢问题

    # 确定 按钮可能被一个 div.el-dialog__wrapper 元素遮盖，点击失败。方案1,2如下：
    # WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(
    #     EC.visibility_of_element_located(
    #         (By.CSS_SELECTOR,
    #          'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))
    # ).click()  # 随堂测试 确定

    sleep(.2) # 等待，提升稳定性

    # 方案1：使用 javascript 进行点击
    button = WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR,
             'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))
    )
    driver.execute_script("arguments[0].click();", button)

    # # 方案2：等待元素可点击（未测试）
    # WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(
    #     EC.element_to_be_clickable(
    #         (By.CSS_SELECTOR,
    #          'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))
    # ).click()

    ans_dic = {}  # 答案字典    
    # 获取所有 下一题/交卷 按钮
    next_n_submit_buttons = driver.find_elements(By.CSS_SELECTOR, 'div.bast_quest_btn')[1::2]

    trial_num = int(driver.find_element(By.CSS_SELECTOR,
                                        'div[class="top_e"] div').text.split('/')[1])  # 题目数
    print(f'进入测试，共 {trial_num} 题')

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
            next_n_submit_buttons[i].click()  # 点击 下一题（或交卷）
            if i == trial_num - 1:
                # 解决可能不点击 交卷 的问题
                try:
                    sleep(.5)
                    next_n_submit_buttons[i].click()
                except:
                    print('已点击 交卷')                

                WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'button[class="el-button el-button--default el-button--small el-button--primary "]'))).click()  # 交卷 确定

                result_info = WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'div[class="infoclass"]'))).text  # 获取测试结果

                if result_info.split('\n')[0][-3:] == '不合格':  # 测试不合格
                    WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--default el-button--mini"]'))).click()  # 回看试题

                    # 因为通过测试，肯定有打错的，此处先处理所有题目全部答错的情况
                    # 全部答错的情况下，直接尝试获取正确题目为空，超时报错
                    wrong_answers = WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(
                        EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'li[class="activess isred"]')))
                    wrong_answers_num = len(wrong_answers)
                    if not wrong_answers_num == trial_num:
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
                    print(
                        f'测试未通过（答对 {trial_num-wrong_answers_num}/{trial_num}），答案已记录，再次进行测试')

                    all_trials = WebDriverWait(driver, TIMEOUT_SEC).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'div[class="scroll_content"]')))  # 重新获取所有题目 题干、选项、按钮
                    
                    # 重新获取一次
                    next_n_submit_buttons = driver.find_elements(By.CSS_SELECTOR, 'div.bast_quest_btn')[1::2]

                else:
                    WebDriverWait(driver, TIMEOUT_SEC + wait_longer_sec).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button modelBtn exitBtn  el-button--primary el-button--mini"]'))).click()  # 通过测试，退出
                    print('通过测试')
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
driver.maximize_window()  # 窗口最大化

# 以下页面操作
login()
get_credit_hours()


# 学习课程
while True:
    info, course_status = get_course_to_learn()
    learn_course(course_info=info, watch_video=course_status)


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
