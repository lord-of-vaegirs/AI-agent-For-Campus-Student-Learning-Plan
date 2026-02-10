import streamlit as st
import sys
import os

# --- 1. 修复路径导入逻辑 ---
# 获取当前文件的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 定位到项目的根目录 (back 和 front 的父目录)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
# 将 back 文件夹加入系统路径
back_path = os.path.join(project_root, "back")

if back_path not in sys.path:
    sys.path.append(back_path)

# 尝试导入后端函数
try:
    from register import (
        register_user, 
        get_mandatory_roadmap, 
        get_selection_options, 
        update_user_progress
    )
except ImportError as e:
    st.error(f"⚠️ 导入后端逻辑失败: {e}")
    # 备用模拟逻辑（防止页面完全崩溃）
    def register_user(data): return True, "user_0000000000"
    def get_mandatory_roadmap(uid): return []
    def get_selection_options(uid): return {"courses":[], "research":[], "contests":[]}
    def update_user_progress(uid, data): return False

# --- 2. 页面配置 ---
st.set_page_config(page_title="智航 - AI 学业导航系统", layout="wide")

# 初始化 Session State
if 'step' not in st.session_state:
    st.session_state.step = "registration"
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- 3. 页面逻辑：注册 ---
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
                # 调用后端逻辑
                success, result = register_user(user_data)
                
                if success:
                    st.session_state.user_id = result 
                    st.session_state.user_info = user_data
                    st.success(f"注册成功！您的 ID 为: {result}")
                    
                    if current_semester == 1:
                        st.session_state.step = "new_student_map"
                    else:
                        st.session_state.step = "input_history"
                    st.rerun()
                else:
                    st.error(f"注册失败: {result}")
            else:
                st.error("请完整填写必填信息 (*)")

# --- 4. 页面逻辑：新生必修地图 ---
elif st.session_state.step == "new_student_map":
    st.title(f"📍 必修课程地图 - {st.session_state.user_info['name']}")
    st.info(f"系统已根据您的专业生成全学期必修课时间轴。")

    roadmap = get_mandatory_roadmap(st.session_state.user_id)

    if roadmap:
        # 按学期分组显示
        for sem in range(1, 9):
            sem_courses = [c for c in roadmap if c['semester'] == sem]
            if sem_courses:
                st.write(f"### 第 {sem} 学期")
                cols = st.columns(len(sem_courses))
                for i, course in enumerate(sem_courses):
                    with cols[i]:
                        st.success(f"**{course['name']}**\n\n({course['credits']} 学分)")
    else:
        st.warning("未找到必修课程数据，请检查课程数据库。")

    if st.button("下一步：进入个人仪表盘"):
        st.info("仪表盘功能开发中...")

# --- 5. 页面逻辑：老生录入历史 ---
elif st.session_state.step == "input_history":
    st.title(f"🔍 欢迎回来，{st.session_state.user_info['name']}！")
    
    # 获取包含奖项信息的选项
    all_options = get_selection_options(st.session_state.user_id)
    
    with st.container():
        st.write("### 1. 课程记录")
        sel_courses = st.multiselect("已修读课程", options=all_options['courses'])
        course_data = []
        for name in sel_courses:
            c1, c2, c3 = st.columns([2,1,1])
            with c1: st.write(f"**{name}**")
            with c2: grade = st.number_input("绩点", 0.0, 4.0, 4.0, 0.1, key=f"g_{name}")
            with c3: sem = st.number_input("学期", 1, 8, 1, key=f"s_{name}")
            course_data.append({"name": name, "grade": grade, "semester": sem, "category": "必修/选修"})

        st.divider()
        st.write("### 2. 科研经历")
        sel_res = st.multiselect("参与科研", options=all_options['research'])
        res_data = []
        for rname in sel_res:
            c1, c2 = st.columns([3,1])
            with c1: st.write(rname)
            with c2: r_sem = st.number_input("完成学期", 1, 8, 1, key=f"rs_{rname}")
            res_data.append({"name": rname, "complete_semester": r_sem})

        st.divider()
        st.write("### 3. 竞赛获奖")
        # 使用返回的 contest_list 作为可选项
        sel_con = st.multiselect("参加竞赛", options=all_options.get('contest_list', []))
        con_data = []
        
        # 获取后端传来的奖项字典
        award_map = all_options.get('contest_awards', {})
        
        for cname in sel_con:
            c1, c2, c3 = st.columns([2,1,1])
            with c1: st.write(cname)
            with c2: 
                # 动态获取当前竞赛对应的奖项列表，如果没有则默认参与奖
                current_awards = award_map.get(cname, ["参与奖"])
                award = st.selectbox("获得奖项", options=current_awards, key=f"ca_{cname}")
            with c3: 
                con_sem = st.number_input("获奖学期", 1, 8, 1, key=f"cs_{cname}")
            con_data.append({"name": cname, "award": award, "complete_semester": con_sem})

    if st.form_submit_button("提交并生成学业画像") if 'form' in locals() else st.button("提交并生成学业画像", type="primary"):
        payload = {
            "courses": course_data,
            "research": res_data,
            "competitions": con_data
        }
        if update_user_progress(st.session_state.user_id, payload):
            st.success("更新成功！")
        else:
            st.error("数据更新失败，请检查后端 Python 终端报错信息。")
    if st.button("返回"):
        st.session_state.step = "registration"
        st.rerun()