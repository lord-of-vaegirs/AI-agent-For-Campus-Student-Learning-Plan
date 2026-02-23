import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go
from collections import defaultdict

# --- 1. 路径修复与后端导入 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
back_path = os.path.join(project_root, "back")
if back_path not in sys.path:
    sys.path.append(back_path)

try:
    from register import (
        register_user, login_user, get_mandatory_roadmap, 
        get_selection_options, update_user_progress, get_db_data,
        update_current_semester, graduate_warning 
    )
    from recommend import stream_conversation_for_plan 
    from comment import record_comment, add_like
    from match import stream_conversation_for_match
    from rank import generate_comment_rank_list
except ImportError as e:
    st.error(f"❌ 无法加载后端模块: {e}")

# --- 2. 页面配置与全局美化 CSS ---
st.set_page_config(page_title="智航 - AI 学业导航系统", layout="wide")

# 注入自定义 CSS 提升视觉效果
st.markdown("""
    <style>
    /* 美化指标卡片 */
    [data-testid="stMetricValue"] {
        font-size: 32px;
        color: #1E88E5;
        font-weight: 700;
    }
    /* 美化 Tab 标题 */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 18px;
        font-weight: 600;
    }
    /* 调整容器间距 */
    .stAlert {
        border-radius: 10px;
    }
            /* 全局背景设置 */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); /* 浅蓝色科技渐变 */
        background-attachment: fixed;
    }

    /* 侧边栏背景（可选） */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px); /* 磨砂玻璃效果 */
    }

    /* 主容器美化：让内容区带一点白色半透明感，更易阅读 */
    .main .block-container {
        background-color: rgba(255, 255, 255, 0.6);
        border-radius: 20px;
        padding: 3rem;
        margin-top: 2rem;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
    }
            /* 定义艺术字类 */
    .artistic-title {
        font-family: 'Microsoft YaHei', sans-serif;
        font-size: 48px !important;
        font-weight: 800;
        background: linear-gradient(45deg, #1E88E5, #1565C0, #43A047);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 2px 2px 10px rgba(30, 136, 229, 0.2);
        margin-bottom: 20px;
        text-align: center;
    }
    
    .artistic-subtitle {
        font-size: 20px;
        color: #555;
        text-align: center;
        font-style: italic;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# 初始化 Session State 状态
if 'step' not in st.session_state: st.session_state.step = "login"
if 'user_id' not in st.session_state: st.session_state.user_id = ""
if 'needs_reset' not in st.session_state: st.session_state.needs_reset = False
if "messages" not in st.session_state: st.session_state.messages = []
if "matched_uids" not in st.session_state: st.session_state.matched_uids = []
if 'comment_version' not in st.session_state: st.session_state.comment_version = 0

# --- 3. 登录页面 ---
if st.session_state.step == "login":
    st.markdown('<p class="artistic-title">✨ 智航学业导航系统</p>', unsafe_allow_html=True)
    col_l, _ = st.columns([1, 2])
    with col_l:
        sid_input = st.text_input("请输入学工号登录", placeholder="10位阿拉伯数字")
        if st.button("登录", type="primary", width='stretch'):
            success, msg_or_id, data = login_user(sid_input)
            if success:
                st.session_state.user_id = msg_or_id
                
                # 🚩 修改点 1：登录成功后清空旧的匹配结果和聊天记录
                st.session_state.matched_uids = []
                st.session_state.messages = []

                update_current_semester(msg_or_id)
                st.session_state.step = "dashboard"
                st.rerun()
            else:
                st.error(msg_or_id)
        st.divider()
        if st.button("新同学？点击注册账号", width='stretch'):
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
        
        submit_reg = st.form_submit_button("完成注册并进入系统", type="primary")
        
        if submit_reg:
            if name and sid and major:
                reg_payload = {
                    "name": name, 
                    "student_id": sid, 
                    "enrollment_year": year, 
                    "school": school, 
                    "major": major, 
                    "target": target, 
                    "current_semester": 1 
                }
                success, res = register_user(reg_payload)
                if success:
                    st.session_state.user_id = res
                    
                    # 🚩 修改点 2：注册成功后清空旧的匹配结果和聊天记录
                    st.session_state.matched_uids = []
                    st.session_state.messages = []

                    update_current_semester(res)
                    st.session_state.step = "dashboard"
                    st.rerun()
                else:
                    st.error(res)
            else:
                st.error("请填写必填项")

    st.write("") 
    if st.button("已有账号？返回登录", width='stretch'):
        st.session_state.step = "login"
        st.rerun()

# --- 5. 系统核心主页面 (Dashboard) ---
elif st.session_state.step == "dashboard":
    if st.session_state.needs_reset:
        st.session_state["ms_c"] = []; st.session_state["ms_ct"] = []; st.session_state["ms_r"] = []
        st.session_state.needs_reset = False

    all_users = get_db_data("users.json")
    user = all_users.get(st.session_state.user_id)
    if not user: st.session_state.step = "login"; st.rerun()

    #st.title(f"智航看板 - 欢迎您，{user['profile']['name']}")
    st.markdown(f'''
        <div style="display: flex; align-items: center;">
            <span style="font-size: 42px; margin-right: 15px;"></span>
            <h1 class="artistic-title">智航看板 - 欢迎您，{user["profile"]["name"]}</h1>
        </div>
    ''', unsafe_allow_html=True)
    # 毕业预警板块
    warning_result = graduate_warning(st.session_state.user_id)
    if warning_result[0]:
        _, must_tasks, credit_gaps = warning_result
        with st.container(border=True):
            st.error("**毕业预警：您的修读进度滞后**")
            cw1, cw2 = st.columns(2)
            with cw1:
                st.write("🔴 **待修必修课：**")
                for task in must_tasks: st.write(f"- {task.get('name')} (建议第{task.get('semester')}学期)")
            with cw2:
                st.write("🟡 **学分缺口：**")
                for gap in [g for g in credit_gaps if float(g.get("course_gap", 0)) > 0]:
                    st.write(f"- **{gap.get('category')}**: 缺 {gap.get('course_gap')} 门")
        st.divider()
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1: st.metric("已修总学分", f"{user.get('total_credits', 0.0)} pts")
    with col_stat2: st.metric("平均加权绩点 (GPA)", f"{user.get('average_grades', 0.0):.2f}")
    with col_stat3: st.metric("当前学期", f"第 {user['academic_progress']['current_semester']} 学期")
    with col_stat4: 
        rank_val = user.get('path_review', {}).get('current_rank', '-')
        st.metric("路径影响力排名", f"No.{rank_val}")

    st.divider()

    with st.sidebar:
        st.header("功能中心")
        if st.button("开启 AI 智能规划", width='stretch', type="primary"):
            st.session_state.step = "recommendation"; st.rerun()
        st.divider()
        if st.button("退出登录", width='stretch'):
            # 🚩 修改点 3：退出登录时清空匹配记录
            st.session_state.matched_uids = []
            st.session_state.step = "login"
            st.rerun()

    tab_input, tab_tree, tab_radar, tab_map, tab_match, tab_rank = st.tabs([
        "录入成就", "知识技能树", "能力雷达图", "必修地图", "路径匹配与复盘", "荣誉排行榜"
    ])

    with tab_input:
        st.subheader("记录本学期新内容")
        opts = get_selection_options(st.session_state.user_id)
        history = user.get('academic_progress', {})
        existing_c = {item['name'] for item in history.get('completed_courses', [])}
        existing_ct = {item['name'] for item in history.get('competitions_done', [])}
        existing_r = {item['name'] for item in history.get('research_done', [])}

        st.write("#### 📘 新增课程修读")
        sel_c = st.multiselect("选择完成的课程", options=opts.get('courses', []), key="ms_c")
        course_new = []
        for n in sel_c:
            if n in existing_c: st.warning(f"💡 课程【{n}】已在记录中。"); continue
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1: st.info(f"**{n}**")
            with c2: g = st.number_input(f"绩点", 0.0, 4.0, 4.0, 0.1, key=f"g_{n}")
            with c3: s = st.number_input(f"学期", 1, 8, user['academic_progress']['current_semester'], key=f"s_{n}")
            course_new.append({"name": n, "grade": g, "semester": s})

        st.divider()
        st.write("#### 🏆 新增竞赛获奖")
        sel_ct = st.multiselect("选择参加的竞赛", options=opts.get('contest_list', []), key="ms_ct")
        contest_new = []
        award_map = opts.get('contest_awards', {})
        for n in sel_ct:
            if n in existing_ct: st.warning(f"💡 竞赛【{n}】已在记录中。"); continue
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1: st.success(f"**{n}**")
            with col2: a = st.selectbox(f"奖项", options=award_map.get(n, ["参与奖"]), key=f"a_{n}")
            with col3: cs = st.number_input("获奖学期", 1, 8, user['academic_progress']['current_semester'], key=f"cs_{n}")
            contest_new.append({"name": n, "award": a, "complete_semester": cs})

        st.divider()
        st.write("#### 🧪 新增科研项目")
        sel_r = st.multiselect("选择参与的科研", options=opts.get('research', []), key="ms_r")
        research_new = []
        for n in sel_r:
            if n in existing_r: st.warning(f"💡 科研【{n}】已在记录中。"); continue
            col1, col2 = st.columns([3, 1])
            with col1: st.info(f"项目名称：**{n}**")
            with col2: rs = st.number_input("完成学期", 1, 8, user['academic_progress']['current_semester'], key=f"rs_{n}")
            research_new.append({"name": n, "complete_semester": rs})

        if st.button("同步数据并更新能力画像", type="primary", width='stretch'):
            if not course_new and not contest_new and not research_new: st.warning("未检测到新内容。")
            else:
                final_payload = {"courses": history.get('completed_courses', []) + course_new, "research": history.get('research_done', []) + research_new, "competitions": history.get('competitions_done', []) + contest_new}
                if update_user_progress(st.session_state.user_id, final_payload):
                    st.session_state.needs_reset = True; st.success("🎉 更新成功！"); st.rerun()

    with tab_tree:
        st.subheader("🌲 知识维度积累分布")
        k_data = user.get('knowledge', {})
        if k_data:
            df_k = pd.DataFrame({"维度": list(k_data.keys()), "分值": list(k_data.values())}).sort_values(by="分值")
            fig_k = go.Figure(go.Bar(x=df_k["分值"], y=df_k["维度"], orientation='h', marker=dict(color=df_k["分值"], colorscale='Blues', line=dict(color='white', width=1)), text=df_k["分值"], textposition='outside'))
            fig_k.update_layout(height=400, margin=dict(l=10, r=40, t=10, b=10), xaxis_title="积累得分", plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_k, width='stretch')
        else: st.info("尚无数据")

    with tab_radar:
        st.subheader("🕸️ 核心能力模型")
        s_data = user.get('skills', {})
        if s_data:
            categories = list(s_data.keys()); values = list(s_data.values())
            fig_s = go.Figure(go.Scatterpolar(r=values+[values[0]], theta=categories+[categories[0]], fill='toself', fillcolor='rgba(30, 136, 229, 0.4)', line=dict(color='#1E88E5', width=3)))
            fig_s.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(values)+20 if values else 100], gridcolor="#EEE")), height=500, showlegend=False)
            st.plotly_chart(fig_s, width='stretch')

    with tab_map:
        st.subheader("专业必修课路线图")
        target_roadmap = []
        courses_db = get_db_data("courses.json")
        for college in courses_db.get("学院列表", []):
            if college.get("学院名称") == user['profile'].get('school'):
                for major_item in college.get("专业列表", []):
                    if major_item.get("专业名称") == user['profile'].get('major'):
                        target_roadmap = major_item.get("course_map", [])
                        break
        if target_roadmap:
            target_roadmap.sort(key=lambda x: x.get("semester", 1))
            for s in range(1, 9):
                s_courses = [c for c in target_roadmap if int(c.get('semester', 0)) == s]
                if s_courses:
                    st.markdown(f"#### 第 {s} 学期")
                    cols = st.columns(len(s_courses))
                    for i, c in enumerate(s_courses): cols[i].success(f"**{c['name']}**\n\n{c.get('credits', 0)}学分")
        else: st.warning("暂无地图数据。")

    with tab_match:
        st.subheader("🏁 我的成长复盘")
        path_review = user.get("path_review", {})
        c_p1, c_p2 = st.columns([2, 1])
        with c_p1: st.info(f"**我的当前路径复盘评价：**\n\n{path_review.get('content', '暂未填写')}")
        with c_p2:
            st.write(f"❤️ 累计获得点赞：**{path_review.get('like_count', 0)}**")
            st.write(f"🏆 当前影响力排名：**No.{path_review.get('current_rank', '-')}**")

        with st.expander("撰写/修改我的全路径评价"):
            new_comment_text = st.text_area("分享你的经验指南或心得：", placeholder="在此输入新内容...", height=150, key=f"my_comment_box_{st.session_state.comment_version}")
            if st.button("提交评价"):
                if new_comment_text:
                    if record_comment(st.session_state.user_id, new_comment_text):
                        st.session_state.comment_version += 1; generate_comment_rank_list(); st.success("已存入！"); st.rerun()
                else:
                    st.warning("内容不能为空")

        st.divider()
        st.subheader("AI 路径匹配")
        if st.button("开始匹配相似路径", type="primary"):
            with st.spinner("AI 正在分析路径..."):
                st.session_state.matched_uids = stream_conversation_for_match(st.session_state.user_id)
        
        # 匹配结果展示逻辑
        if st.session_state.matched_uids:
            c_db = get_db_data("courses.json"); r_db = get_db_data("research.json"); ct_db = get_db_data("contests.json")
            desc_lookup = {}
            for col in c_db.get("学院列表", []):
                for m in col.get("专业列表", []):
                    for c in m.get("课程列表", []): desc_lookup[c['name']] = c.get('course_introduction', "暂无介绍")
            for col in r_db.get("学院列表", []):
                for m in col.get("专业列表", []):
                    for r in m.get("科研列表", []): desc_lookup[r['name']] = r.get('abstract', "暂无简介")
            for col in ct_db.get("学院列表", []):
                for m in col.get("专业列表", []):
                    for ct in m.get("竞赛列表", []): desc_lookup[ct['name']] = ct.get('description', "暂无简介")

            for m_uid in st.session_state.matched_uids:
                peer = all_users.get(m_uid)
                if not peer: continue
                with st.container(border=True):
                    header_col, like_col = st.columns([5, 1])
                    with header_col: st.markdown(f"### 目标：{peer['profile']['target']} ({peer['profile']['major']})")
                    with like_col:
                        if st.button(f"👍 {peer.get('path_review', {}).get('like_count', 0)}", key=f"like_{m_uid}"):
                            if add_like(m_uid): st.rerun()
                    st.write(f"💬 **复盘经验：** {peer.get('path_review', {}).get('content', '暂无评价')}")
                    p_col1, p_col2, p_col3 = st.columns(3)
                    with p_col1:
                        st.write("📘 **修读课程**")
                        course_groups = defaultdict(list)
                        for c in peer['academic_progress'].get('completed_courses', []): course_groups[c['semester']].append(c['name'])
                        for sem in sorted(course_groups.keys()):
                            with st.popover(f"第 {sem} 学期课程"):
                                for cname in course_groups[sem]: st.write(f"• {cname}")
                    with p_col2:
                        st.write("🏆 **参与竞赛**")
                        for ct in peer['academic_progress'].get('competitions_done', []):
                            with st.popover(f"Sem {ct['complete_semester']}: {ct['name']}"):
                                st.write(f"**获得奖项：** {ct.get('award', '未填写')}"); st.info(desc_lookup.get(ct['name'], "暂无详情"))
                    with p_col3:
                        st.write("🧪 **科研项目**")
                        for rs in peer['academic_progress'].get('research_done', []):
                            with st.popover(f"Sem {rs['complete_semester']}: {rs['name']}"):
                                st.write("**项目简介：**"); st.info(desc_lookup.get(rs['name'], "暂无详情"))

    with tab_rank:
        st.subheader("🏆 全校路径贡献榜 (Top 30)")
        rank_list = generate_comment_rank_list()
        if rank_list:
            df_rank = pd.DataFrame(rank_list[:30])
            df_rank['当前排名'] = df_rank['current_rank'].apply(lambda x: f"🥇 第{x}名" if x==1 else (f"🥈 第{x}名" if x==2 else (f"🥉 第{x}名" if x==3 else f"第{x}名")))
            df_display = df_rank[['当前排名', 'user_name', 'like_count']]
            df_display.columns = ["荣誉排行", "贡献者姓名", "收获点赞 ❤️"]
            st.dataframe(df_display, width='stretch', hide_index=True)
        else: st.info("榜单尚未生成。")

# --- 6. 推荐页面 ---
elif st.session_state.step == "recommendation":
    all_users = get_db_data("users.json"); user = all_users.get(st.session_state.user_id)
    st.title("AI 智能学业规划导师")
    st.markdown(f"#### 您好，{user['profile']['name']}！")
    st.markdown(f"""
我是您的专属学业数字助手。我已经调取了您的**专业培养方案、当前绩点、已点亮的技能树**以及您设定的**{user['profile']['target']}**目标。

您可以向我咨询任何关于选课、竞赛、科研或职业发展的疑问，我会根据您的个人实际情况给出量身定制的规划建议。
""")
    st.divider()
    with st.sidebar:
        if st.button("返回主面板"): st.session_state.step = "dashboard"; st.rerun()
        if st.button("清空历史"): st.session_state.messages = []; st.rerun()
    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"])
    if prompt := st.chat_input("您可以向我咨询规划建议..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            status_p = st.empty(); status_p.info("正在为您规划方案..."); container = {"first": False}
            try:
                res_gen = stream_conversation_for_plan(st.session_state.user_id, prompt)
                def wrapped():
                    for chunk in res_gen:
                        if not container["first"]: status_p.empty(); container["first"] = True
                        yield chunk
                full_res = st.write_stream(wrapped())
                st.session_state.messages.append({"role": "assistant", "content": full_res})
            except Exception as e: status_p.empty(); st.error(f"对话出错：{str(e)}")