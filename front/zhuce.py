import streamlit as st
import sys
import os

# --- 🚩 后端函数接入点 ---
# 建议新建一个 register.py 文件放在同级目录，让同学 A 在里面写这四个函数
# 如果 register.py 还没写好，下面的 try-except 会保证你的前端能运行演示
sys.path.append(os.path.join(os.path.dirname(__file__), "../back"))

try:
    from register import (
        register_user, 
        get_mandatory_roadmap, 
        get_selection_options, 
        update_user_progress
    )
except ImportError:
    st.error("⚠️ 未找到 register.py。请确保后端同学已创建该文件。目前使用模拟逻辑运行。")
    # 模拟逻辑，防止代码崩溃
    def register_user(data): return True, f"user_{str(data['student_id']).zfill(10)}"
    def get_mandatory_roadmap(uid): return []
    def get_selection_options(): return {"courses":[], "research":[], "contests":[]}
    def update_user_progress(uid, data): return True

# --- 页面配置 ---
st.set_page_config(page_title="智航 - AI 学业导航系统", layout="wide")

# --- 初始化 Session State ---
if 'step' not in st.session_state:
    st.session_state.step = "registration"
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- 1. 注册页面 ---
if st.session_state.step == "registration":
    st.title("🚀 智航 - 开启您的 AI 学业个人导航")
    st.subheader("请填写基本信息以初始化您的学业画像")

    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("姓名 *", placeholder="请输入真实姓名")
            student_id = st.text_input("学工号 (10位) *", placeholder="2023000001")
            enrollment_year = st.selectbox("入学年份", [2022, 2023, 2024, 2025], index=2)
        with col2:
            school = st.selectbox("学院", ["信息学院", "高瓴人工智能学院", "理学院", "其他"])
            major = st.text_input("专业 *", placeholder="如：计算机科学与技术")
            target = st.selectbox("最终目标", ["保研", "出国深造", "本科就业", "考研", "不确定"])

        current_semester = st.slider("当前所处学期", 1, 8, 1)
        submit_button = st.form_submit_button("进入系统")

        if submit_button:
            if name and student_id and major:
                user_data = {
                    "name": name, "student_id": student_id, "enrollment_year": enrollment_year,
                    "school": school, "major": major, "target": target, "current_semester": current_semester
                }
                # 🚩 调用后端逻辑：注册并初始化 JSON
                success, result = register_user(user_data)
                
                if success:
                    st.session_state.user_id = result # 保存返回的 user_xxxxxxxxxx
                    st.session_state.user_info = user_data
                    st.success(f"注册成功！您的 ID 为: {result}")
                    
                    # 根据学期决定下一步
                    if current_semester == 1:
                        st.session_state.step = "new_student_map"
                    else:
                        st.session_state.step = "input_history"
                    st.rerun()
            else:
                st.error("请完整填写必填信息 (*)")

# --- 2. 新生模式：必修课程地图 ---
elif st.session_state.step == "new_student_map":
    st.title(f"📍 必修课程地图 - {st.session_state.user_info['name']}")
    st.info(f"系统已根据您的专业生成全学期必修课时间轴。")

    # 🚩 调用后端逻辑：获取必修课列表
    # 后端 A 同学需要实现：根据 user_id 查专业，从课程库提取必修课并存入用户数据库
    roadmap = get_mandatory_roadmap(st.session_state.user_id)

    if roadmap:
        # 这里你可以发挥前端功力，用卡片形式展示课程
        for sem in range(1, 9):
            sem_courses = [c for c in roadmap if c['semester'] == sem]
            if sem_courses:
                st.write(f"### 第 {sem} 学期")
                cols = st.columns(len(sem_courses))
                for i, course in enumerate(sem_courses):
                    with cols[i]:
                        st.success(f"**{course['name']}**")
    else:
        st.write("⏳ 正在由 AI 解析培养方案中，请稍后刷新...")

    if st.button("进入个人仪表盘"):
        # st.session_state.step = "dashboard"
        # st.rerun()
        pass

# --- 3. 老生模式：录入已完成历史 ---
elif st.session_state.step == "input_history":
    st.title(f"🔍 欢迎回来，{st.session_state.user_info['name']}！")
    st.info(f"请录入您在大一至当前学期间完成的内容，以便 AI 为您精准规划。")

    # 🚩 调用后端逻辑：获取下拉框选项
    # 后端 A 同学需要实现：从 courses.json, research.json, contests.json 提取所有名字
    options = get_selection_options()

    with st.form("history_input_form"):
        st.write("##### 1. 已完成课程")
        done_courses = st.multiselect("请选择已修课程", options=options.get('courses', []))
        
        st.divider()
        st.write("##### 2. 已参与科研 & 竞赛")
        done_research = st.multiselect("已参与科研", options=options.get('research', []))
        done_contests = st.multiselect("已参加竞赛", options=options.get('contests', []))

        if st.form_submit_button("提交历史数据"):
            history_payload = {
                "courses": done_courses,
                "research": done_research,
                "contests": done_contests
            }
            # 🚩 调用后端逻辑：提交并计算技能树
            if update_user_progress(st.session_state.user_id, history_payload):
                st.success("数据已同步，正在为您点亮技能树...")
                # st.session_state.step = "dashboard"
                # st.rerun()