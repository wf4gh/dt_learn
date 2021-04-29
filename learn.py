from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep

login_url = 'https://sso.dtdjzx.gov.cn/sso/login'
redirect_url = 'https://gbwlxy.dtdjzx.gov.cn/oauth2/login/pro'
courses_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/commendIndex' # 课程
subjects_url = 'https://gbwlxy.dtdjzx.gov.cn/content#/projectIndex' # 专题

def lg(s): # log
    print(s)

class TheSite:

    def __init__(self, driver):
        self.driver = driver
        self.subject_to_learn = None # 要学习的专题
        self.page_to_learn = None # 要学习的具体课程（专题或课程中）
        self.driver.maximize_window()
        self.timeout_sec = 10

    def login(self):
        self.driver.get(login_url)
        # 等待用户登录
        lg('等待登录')
        WebDriverWait(self.driver, 300).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, f'a[href="{redirect_url}"]')))
        sleep(1)
        lg('已登录')
        self.driver.get(redirect_url)
        lg('已跳转')
        sleep(.1)

    def to_course_page(self, target_page_num=1):  # 进入【课程推荐】，并跳转至第target_page_num页
        # lg(f'将跳转至第 {target_page_num} 页')
        sleep(1)
        self.driver.get(courses_url)
        current_page = 1
        while current_page < target_page_num:
            sleep(.1)
            WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, 'i[class="el-icon el-icon-arrow-right"]'))).click()  # 点击 下一页
            current_page = int(WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, 'li[class="number active"]'))).text)  # 获取新的当前页码
        # lg(f'已跳转至第 {target_page_num} 页')

    def get_course_to_learn(self):
        self.to_course_page(1)
        lg('搜索当前页面未完成课程')
        while True:
            sleep(1)
            course_elems = WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_all_elements_located(
                (By.CSS_SELECTOR, 'div[class="video-warp-start"]')))  # 获取当前页面课程
            for course_elem in course_elems:
                if course_elem.text[-3:] != '已学习':
                    self.page_to_learn = course_elem

                    course_name = course_elem.text.split('\n')[0]
                    if course_elem.text[-3:] == '过考试':
                        lg(f'准备 {course_name} 测试')
                        return False # 是否需要视频学习
                    else:
                        lg(f'准备学习 {course_name}')
                        return True # 是否需要视频学习
                        
            WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'i[class="el-icon el-icon-arrow-right"]'))).click()  # 当前页面所有课程已学习，点击 下一页
            lg('当前页面所有课程已学习，进入下一页搜索')
    
    def to_subject(self): # TODO 翻页
        sleep(1)
        self.driver.get(subjects_url) # 进入 专题 页面
        WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located((By.XPATH, '//p[text()="正在举办"]'))).click() # 确保进入 正在举办 tab
        # cur_tab_elem = WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[class="content-tab active-content"]'))) # 获取此tab下内容
        sleep(1)
        subjects = WebDriverWait(self.driver, self.timeout_sec).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class="course-list-item-message"]'))) # 获取课程信息
        # subjects = cur_tab_elem.find_elements_by_css_selector('div[class="course-list-item-message"]') # 获取课程信息
        subjects_status = [s.find_elements_by_xpath('p')[1].text.split('\n')[-1] for s in subjects] # 课程报名状态
        attended_idx = subjects_status.index('已报名') ###### 学习 已报名 # TODO 自动报名
        self.subject_to_learn = subjects[attended_idx]

    def get_subject_course_to_learn(self):
        sleep(.5)
        self.subject_to_learn.click()
        sleep(2)
        next_button = WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[class="btn-next"]')))
        is_compulsory = True # 默认进入必修课程
        # while not next_button.is_enabled():
        sleep(.5)
        page_cnt = len(self.driver.find_elements_by_css_selector('li[class="number"]')) + 1
        cur_active = int(self.driver.find_element_by_css_selector('li[class="number active"]').text)

        while cur_active <= page_cnt:
            sleep(1)
            courses = WebDriverWait(self.driver, self.timeout_sec).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class="course-list-item-message"]'))) # 获取所有学习状态按钮 （ 已学习 / 未学习 ）
            valid_courses = [c for c in courses if c.text != '']
            for c in valid_courses:
                if c.text[-3:] != '已学习':
                    self.page_to_learn = c.find_element_by_css_selector('h2')
                    course_name = c.text.split('\n')[0]
                    if c.text[-3:] == '过考试':
                        lg(f'准备 {course_name} 测试')
                        return False # 是否需要视频学习
                    else:
                        lg(f'准备学习 {course_name}')
                        return True # 是否需要视频学习
            next_button.click()
            sleep(.5)
            cur_active = int(self.driver.find_element_by_css_selector('li[class="number active"]').text)
            if is_compulsory and (not next_button.is_enabled()): # 必修课程遍历完毕，进入选修课程
                self.driver.find_element_by_xpath('//p[text()="选修课程"]').click()
                is_compulsory = False
                assert next_button.is_enabled()
            lg('当前页面所有课程已学习，进入下一页搜索')

    def learn_course(self, watch_video=True, is_subject_course=False):
        sleep(.5)
        self.page_to_learn.click()  # 进入视频播放页
        WebDriverWait(self.driver, self.timeout_sec).until(EC.new_window_is_opened)
        if is_subject_course: # 专题课程会打开新窗口，进行跳转
            self.driver.switch_to.window(self.driver.window_handles[1])
        sleep(.5)

        if not watch_video: # 不需视频学习，则直接进行测试
            WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'img[class="rightBottom"]'))).click()  # 点击 随堂测试
            self.do_exam()
            return

        play_button = WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'button[title="Play Video"]')))  # 获取播放按钮
        play_button.click()  # 播放
        sleep(.5)
        WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'button[title="Pause"]'))).click()  # 暂停（使视频长度持续显示）

        has_test = True if self.driver.find_element_by_xpath(
            '//div[text()="随堂测试："]/../div[@class="titleContent"]/span').text == '是' else False  # 判断是否有随堂测试

        # 获取视频长度
        dur = 5
        while dur == 5: # 解决获取0：00问题
            sleep(.5)
            mins, secs = self.driver.find_element_by_css_selector(
                'span.vjs-duration-display').text.split(':')
            if mins.isdigit() and secs.isdigit(): # 解决获取 mins:secs 为 -:- 问题
                dur = int(mins) * 60 + int(secs) + 5

        lg(f'视频长度 {mins}:{secs} ，随堂测试: {has_test} ，开始学习')
        sleep(2) # 0.5 -> 2秒，尝试解决 not interactable 问题
        play_button.click()

        sleep(dur)

        if has_test:
            self.do_exam()
        else:
            WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, 'button[title="Replay"]')))

        if is_subject_course: # 关闭专题课程新窗口，跳转回原窗口
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

        lg('此课程学习完成')

    def do_exam(self):
        WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))).click()  # 随堂测试 确定
        lg('进入测试')
        ans_dic = {}  # 答案字典
        all_trials = WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'div[class="scroll_content"]')))  # 获取所有题目 题干、选项、按钮
        next_buttons = all_trials.find_elements_by_xpath(
            '//div[text()="下一题"]')  # 获取所有 下一题/交卷 按钮
        trial_num = int(self.driver.find_element_by_css_selector(
            'div[class="top_e"] div').text.split('/')[1])  # 题目数
        lg(f'测试共有 {trial_num} 道题')

        all_trial_options = self.driver.find_elements_by_css_selector(
            'div[class="options_wraper"]')  # 获取所有题目选项组
        while True:
            for i in range(trial_num):
                options = all_trial_options[i]  # 当前题目选项组
                opt_elems = options.find_elements_by_css_selector(
                    'label')  # 当前题目选项
                opt_counts = len(opt_elems)  # 当前题目选项数

                if i not in ans_dic.keys():  # 第一轮答题
                    cur_type = ''.join([t.text for t in self.driver.find_elements_by_css_selector(
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
                    WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[class="el-button el-button--default el-button--small el-button--primary "]'))).click()  # 交卷 确定

                    result_info = WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'div[class="infoclass"]'))).text  # 获取测试结果

                    lg('已交卷，正在核对答案')

                    if result_info.split('\n')[0][-3:] == '不合格':  # 测试不合格
                        lg('测试未通过')
                        WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--default el-button--mini"]'))).click()  # 回看试题
                        correct_answers = WebDriverWait(self.driver, self.timeout_sec).until(
                            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'li[class="activess"]')))
                        correct_idx = [
                            int(ca.text) - 1 for ca in correct_answers]
                        for idx in correct_idx:
                            ans_dic[idx][1] = 1
                        driver.find_element_by_css_selector(
                            'button[class="el-button exit el-button--default el-button--mini"]').click()  # 退出回看
                        WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, 'img[class="rightBottom"]'))).click()  # 重新进入测试
                        WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, 'button[class="el-button modelBtn doingBtn el-button--primary el-button--mini"]'))).click()  # 确定
                        lg('答案已记录，再次进行测试')

                        all_trials = WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, 'div[class="scroll_content"]')))  # 重新获取所有题目 题干、选项、按钮
                        next_buttons = all_trials.find_elements_by_xpath(
                            '//div[text()="下一题"]')  # 重新获取所有 下一题/交卷 按钮
                        all_trial_options = self.driver.find_elements_by_css_selector(
                            'div[class="options_wraper"]')  # 获取所有题目选项组

                    else:
                        WebDriverWait(self.driver, self.timeout_sec).until(EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, 'button[class="el-button modelBtn exitBtn  el-button--primary el-button--mini"]'))).click()  # 通过测试，退出
                        lg('通过测试')
                        return


driver = webdriver.Chrome()
the_site = TheSite(driver)
the_site.login()

# 学习课程
# while True:
#     course_status = the_site.get_course_to_learn()
#     the_site.learn_course(course_status)

# 学习专题课程
while True:
    the_site.to_subject()
    course_status = the_site.get_subject_course_to_learn()
    the_site.learn_course(course_status, is_subject_course=True)