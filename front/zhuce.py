import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go

# --- 1. 路径修复与后端导入 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
back_path = os.path.join(project_root, "back")
if back_path not in sys.path:
    sys.path.append(back_path)

try:
    from register import (
        register_user, login_user, get_mandatory_roadmap, 
        get_selection_options, update_user_progress, get_db_data
    )
    # 🚩 新增：导入推荐算法函数
    from recommend import stream_conversation_for_plan 
except ImportError as e:
    st.error(f"❌ 无法加载后端模块: {e}")

# --- 2. 页面配置 ---
st.set_page_config(page_title="智航 - AI 学业导航系统", layout="wide")

# 初始化 Session State 状态
if 'step' not in st.session_state:
    st.session_state.step = "login"
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
if 'needs_reset' not in st.session_state:
    st.session_state.needs_reset = False
if "messages" not in st.session_state:
    st.session_state.messages = []
# --- 3. 登录页面 ---
if st.session_state.step == "login":
    st.title("🔐 智航 - 登录系统")
    col_l, _ = st.columns([1, 2])
    with col_l:
        sid_input = st.text_input("请输入学工号登录", placeholder="10位阿拉伯数字")
        if st.button("登录", type="primary", use_container_width=True):
            success, msg_or_id, data = login_user(sid_input)
            if success:
                st.session_state.user_id = msg_or_id
                st.session_state.step = "dashboard"
                st.rerun()
            else:
                st.error(msg_or_id)
        
        st.divider()
        if st.button("新同学？点击注册账号", use_container_width=True):
            st.session_state.step = "registration"
            st.rerun()

# --- 4. 注册页面 ---
elif st.session_state.step == "registration":
    st.title("📝 用户注册")
    with st.form("registration_form_main"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("姓名 *")
            sid = st.text_input("学工号 (10位) *")
            year = st.selectbox("入学年份", [2022, 2023, 2024, 2025], index=2)
        with c2:
            school = st.selectbox("学院", ["信息学院", "高瓴人工智能学院", "理学院"])
            major = st.text_input("专业 *", placeholder="如：计算机科学与技术")
            target = st.selectbox("最终目标", ["保研", "出国深造", "本科就业", "考研"])
        
        sem = st.slider("当前所处学期", 1, 8, 1)
        submit_reg = st.form_submit_button("完成注册并进入系统", type="primary")
        
        if submit_reg:
            if name and sid and major:
                reg_payload = {
                    "name": name, "student_id": sid, "enrollment_year": year,
                    "school": school, "major": major, "target": target, "current_semester": sem
                }
                success, res = register_user(reg_payload)
                if success:
                    st.session_state.user_id = res
                    st.session_state.step = "dashboard"
                    st.rerun()
                else:
                    st.error(res)
            else:
                st.error("请填写必填项")

# --- 5. 系统核心主页面 (Dashboard) ---
elif st.session_state.step == "dashboard":
    # 状态重置检查
    if st.session_state.needs_reset:
        st.session_state["ms_c"] = []
        st.session_state["ms_ct"] = []
        st.session_state["ms_r"] = []
        st.session_state.needs_reset = False

    all_users = get_db_data("users.json")
    user = all_users.get(st.session_state.user_id)
    
    if not user:
        st.session_state.step = "login"; st.rerun()

    # --- 头部展示区：姓名、学分与平均绩点 ---
    st.title(f"📊 智航看板 - 欢迎您，{user['profile']['name']}")
    
    # 🌟 新增：汇总统计卡片
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        # 获取后端计算好的总学分
        tc = user.get("total_credits", 0.0)
        st.metric("已修总学分", f"{tc} pts", help="当前所有已录入课程的学分总和")
    with col_stat2:
        # 获取后端计算好的平均绩点
        avg_g = user.get("average_grades", 0.0)
        st.metric("平均加权绩点 (GPA)", f"{avg_g:.2f}", help="计算公式: Σ(课程绩点 * 课程学分) / 总学分")
    with col_stat3:
        st.metric("当前学期", f"第 {user['academic_progress']['current_semester']} 学期")
    with col_stat4:
        st.metric("规划目标", user['profile']['target'])

    st.divider()

    with st.sidebar:
        st.header("功能中心")
        if st.button("🤖 AI 规划建议", use_container_width=True, type="primary"):
            st.session_state.step = "recommendation"; st.rerun()
        st.divider()
        if st.button("退出登录", use_container_width=True):
            st.session_state.step = "login"; st.rerun()

    tab_input, tab_tree, tab_radar, tab_map = st.tabs(["📝 录入成就", "🌲 知识技能树", "🕸️ 能力雷达图", "🗺️ 必修地图"])

    # --- TAB 1: 录入成就 ---
    with tab_input:
        st.subheader("记录本学期新成就")
        opts = get_selection_options(st.session_state.user_id)
        history = user.get('academic_progress', {})
        existing_c = {item['name'] for item in history.get('completed_courses', [])}
        existing_ct = {item['name'] for item in history.get('competitions_done', [])}
        existing_r = {item['name'] for item in history.get('research_done', [])}

        st.write("#### 📘 新增课程修读")
        sel_c = st.multiselect("搜索并选择完成的课程", options=opts.get('courses', []), key="ms_c")
        course_new = []
        for n in sel_c:
            if n in existing_c:
                st.warning(f"💡 课程【{n}】已在记录中。")
                continue
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1: st.info(f"**{n}**")
            with col2: g = st.number_input(f"绩点", 0.0, 4.0, 4.0, 0.1, key=f"g_{n}")
            with col3: s = st.number_input(f"学期", 1, 8, user['academic_progress']['current_semester'], key=f"s_{n}")
            course_new.append({"name": n, "grade": g, "semester": s, "category": "已修"})

        st.divider()
        st.write("#### 🏆 新增竞赛获奖")
        sel_ct = st.multiselect("搜索并选择参加的竞赛", options=opts.get('contest_list', []), key="ms_ct")
        contest_new = []
        award_map = opts.get('contest_awards', {})
        for n in sel_ct:
            if n in existing_ct:
                st.warning(f"💡 竞赛【{n}】已在记录中。")
                continue
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1: st.success(f"**{n}**")
            with col2: a = st.selectbox(f"奖项", options=award_map.get(n, ["参与奖"]), key=f"a_{n}")
            with col3: cs = st.number_input("获奖学期", 1, 8, user['academic_progress']['current_semester'], key=f"cs_{n}")
            contest_new.append({"name": n, "award": a, "complete_semester": cs})

        st.divider()
        # 3. 科研录入
        st.write("#### 🧪 新增科研项目")
        sel_r = st.multiselect("搜索并选择参与的科研", options=opts.get('research', []), key="ms_r")
        research_new = []
        for n in sel_r:
            if n in existing_r:
                st.warning(f"💡 科研【{n}】已在记录中。")
                continue
            col1, col2 = st.columns([3, 1])
            with col1: 
                # ✅ 使用 st.info 看起来最美观，或者用 st.markdown
                st.info(f"项目名称：**{n}**") 
            with col2: 
                rs = st.number_input("完成学期", 1, 8, user['academic_progress']['current_semester'], key=f"rs_{n}")
            research_new.append({"name": n, "complete_semester": rs})
        if st.button("🚀 同步数据并更新能力画像", type="primary", use_container_width=True):
            if not course_new and not contest_new and not research_new:
                st.warning("未检测到新的录入内容。")
            else:
                final_payload = {
                    "courses": history.get('completed_courses', []) + course_new,
                    "research": history.get('research_done', []) + research_new,
                    "competitions": history.get('competitions_done', []) + contest_new
                }
                # 这里的 update_user_progress 后端已经会更新 GPA 和学分
                if update_user_progress(st.session_state.user_id, final_payload):
                    st.session_state.needs_reset = True
                    st.success("🎉 数据更新成功！学分与平均绩点已实时计算。")
                    st.rerun()

    # --- TAB 2 & 3: 可视化 ---
    with tab_tree:
        st.subheader("🌲 知识维度积累")
        k_data = user.get('knowledge', {})
        if k_data:
            df_k = pd.DataFrame({"维度": list(k_data.keys()), "分值": list(k_data.values())})
            st.bar_chart(df_k, x="维度", y="分值", color="#2ecc71")
    with tab_radar:
        st.subheader("🕸️ 核心能力模型")
        s_data = user.get('skills', {})
        if s_data:
            categories = list(s_data.keys())
            values = list(s_data.values())
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=values+[values[0]], theta=categories+[categories[0]], fill='toself', line_color='#3498db'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(values)+10 if values else 100])), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # --- TAB 4: 必修地图 ---
    with tab_map:
        st.subheader("🗺️ 专业必修课路线图")
        roadmap = get_mandatory_roadmap(st.session_state.user_id)
        if roadmap:
            for s in range(1, 9):
                s_courses = [c for c in roadmap if c['semester'] == s]
                if s_courses:
                    st.markdown(f"**第 {s} 学期**")
                    cols = st.columns(len(s_courses))
                    for i, c in enumerate(s_courses):
                        cols[i].success(f"{c['name']}")

# --- 6. 推荐页面 ---
elif st.session_state.step == "recommendation":
    st.title("🤖 AI 智能学业规划导师")
    st.caption("基于您的技能树、已修课程及科研竞赛背景，为您提供个性化建议。")

    # 侧边栏辅助功能
    with st.sidebar:
        if st.button("⬅️ 返回主面板"):
            st.session_state.step = "dashboard"
            st.rerun()
        if st.button("🗑️ 清空对话历史"):
            st.session_state.messages = []
            st.rerun()

    # 展示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 聊天输入框
    if prompt := st.chat_input("您可以问我：'根据我的背景，下学期选什么课好？' 或 '推荐一些适合我的科研项目'"):
        # 1. 展示并在状态中存储用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. 调用后端流式接口并展示 AI 回复
        with st.chat_message("assistant"):
            # 获取后端生成的生成器
            try:
                response_generator = stream_conversation_for_plan(st.session_state.user_id, prompt)
                
                # 使用 streamlit 的 write_stream 自动处理流式迭代并在界面上“打字”显示
                full_response = st.write_stream(response_generator)
                
                # 3. 将完整回复存入历史记录
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"对话出错：{str(e)}")