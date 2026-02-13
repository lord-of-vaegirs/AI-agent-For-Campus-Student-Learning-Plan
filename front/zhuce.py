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
    # 🚩 新增：导入社交与匹配相关函数
    from comment import record_comment, add_like
    from match import stream_conversation_for_match
    from rank import generate_comment_rank_list
except ImportError as e:
    st.error(f"❌ 无法加载后端模块: {e}")

# --- 2. 页面配置 ---
st.set_page_config(page_title="智航 - AI 学业导航系统", layout="wide")

# 初始化 Session State 状态
if 'step' not in st.session_state: st.session_state.step = "login"
if 'user_id' not in st.session_state: st.session_state.user_id = ""
if 'needs_reset' not in st.session_state: st.session_state.needs_reset = False
if "messages" not in st.session_state: st.session_state.messages = []
# 🚩 新增：存储匹配结果，避免刷新时消失
if "matched_uids" not in st.session_state: st.session_state.matched_uids = []
if 'comment_version' not in st.session_state: st.session_state.comment_version = 0
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
                
                # 🚩 登录成功后：根据当前系统时间自动校准学期
                update_current_semester(msg_or_id)
                
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
                    "current_semester": 1 # 暂传初始值，下一行代码将自动修正它
                }
                success, res = register_user(reg_payload)
                if success:
                    st.session_state.user_id = res
                    
                    # 🚩 核心修改：注册成功后，立即根据“入学年份”和“当前月份”计算真实学期并更新数据库
                    update_current_semester(res)
                    
                    st.session_state.step = "dashboard"
                    st.rerun()
                else:
                    st.error(res)
            else:
                st.error("请填写必填项")

    st.write("") 
    if st.button("已有账号？返回登录", use_container_width=True):
        st.session_state.step = "login"
        st.rerun()

# --- 5. 系统核心主页面 (Dashboard) ---
elif st.session_state.step == "dashboard":
    # 状态重置检查
    if st.session_state.needs_reset:
        st.session_state["ms_c"] = []; st.session_state["ms_ct"] = []; st.session_state["ms_r"] = []
        st.session_state.needs_reset = False

    all_users = get_db_data("users.json")
    user = all_users.get(st.session_state.user_id)
    if not user: st.session_state.step = "login"; st.rerun()

    st.title(f"📊 智航看板 - 欢迎您，{user['profile']['name']}")
# 🚩 2. 核心修改：毕业预警板块展示
    # 每次渲染页面都实时计算一次预警状态
    warning_result = graduate_warning(st.session_state.user_id)
    
    if warning_result[0]: # 如果返回 [True, must_list, gaps_list]
        _, must_tasks, credit_gaps = warning_result
        
        # 使用警告色容器
        with st.container(border=True):
            st.error("🚨 **毕业预警：您的修读进度滞后**")
            st.write("检测到您已进入毕业年级（第7/8学期），但仍有以下关键项未完成：")
            
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.write("🔴 **待修必修课：**")
                if must_tasks:
                    for task in must_tasks:
                        st.write(f"- {task.get('name')} (建议学期: {task.get('semester')})")
                else:
                    st.write("- 无 (必修课已全部修完)")
            
            with col_w2:
                st.write("🟡 **个性化选修/学分缺口：**")
                # 过滤出真正缺分的项
                active_gaps = [g for g in credit_gaps if float(g.get("course_gap", 0)) > 0]
                if active_gaps:
                    for gap in active_gaps:
                        st.write(f"- **{gap.get('category')}**: 缺 {gap.get('course_gap')} 门课程")
                        if gap.get('description'):
                            st.caption(f"  ({gap.get('description')})")
                else:
                    st.write("- 无 (学分要求已满足)")
        st.divider() # 加一个分割线区分预警和正常看板
    
    # 顶部统计卡片
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1: st.metric("已修总学分", f"{user.get('total_credits', 0.0)} pts")
    with col_stat2: st.metric("平均绩点 (GPA)", f"{user.get('average_grades', 0.0):.2f}")
    with col_stat3: st.metric("当前学期", f"第 {user['academic_progress']['current_semester']} 学期")
    with col_stat4: 
        rank_val = user.get('path_review', {}).get('current_rank', '-')
        st.metric("路径影响力排名", f"No.{rank_val}")

    st.divider()

    with st.sidebar:
        st.header("功能中心")
        if st.button("🤖 AI 规划建议", use_container_width=True, type="primary"):
            st.session_state.step = "recommendation"; st.rerun()
        st.divider()
        if st.button("退出登录", use_container_width=True):
            st.session_state.step = "login"; st.rerun()

    # 🚩 核心修改：增加最后两个 Tab
    tab_input, tab_tree, tab_radar, tab_map, tab_match, tab_rank = st.tabs([
        "📝 录入成就", "🌲 知识技能树", "🕸️ 能力雷达图", "🗺️ 必修地图", "🤝 路径匹配与复盘", "🏆 荣誉排行榜"
    ])

    # --- TAB 1, 2, 3, 4 保持原有逻辑 ---
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

        if st.button("🚀 同步数据并更新能力画像", type="primary", use_container_width=True):
            if not course_new and not contest_new and not research_new: st.warning("未检测到新内容。")
            else:
                final_payload = {"courses": history.get('completed_courses', []) + course_new, "research": history.get('research_done', []) + research_new, "competitions": history.get('competitions_done', []) + contest_new}
                if update_user_progress(st.session_state.user_id, final_payload):
                    st.session_state.needs_reset = True; st.success("🎉 更新成功！"); st.rerun()

    with tab_tree:
        st.subheader("🌲 知识维度积累分布")
        k_data = user.get('knowledge', {})
        if k_data:
            df_k = pd.DataFrame({"维度": list(k_data.keys()), "分值": list(k_data.values())}).sort_values(by="分值", ascending=True)
            fig_k = go.Figure(go.Bar(x=df_k["分值"], y=df_k["维度"], orientation='h', marker=dict(color=df_k["分值"], colorscale='Viridis'), text=df_k["分值"], textposition='auto'))
            fig_k.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_k, use_container_width=True)

    with tab_radar:
        st.subheader("🕸️ 核心能力模型")
        s_data = user.get('skills', {})
        if s_data:
            categories = list(s_data.keys()); values = list(s_data.values())
            fig_s = go.Figure(go.Scatterpolar(r=values+[values[0]], theta=categories+[categories[0]], fill='toself', fillcolor='rgba(52, 152, 219, 0.4)', line=dict(color='#3498db', width=3)))
            fig_s.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(values)+20 if values else 100])), showlegend=False)
            st.plotly_chart(fig_s, use_container_width=True)

# --- TAB 4: 必修地图 ---
    with tab_map:
        st.subheader("🗺️ 专业必修课路线图")

        # 1. 获取当前用户的专业和学院信息
        user_major = user['profile'].get('major')
        user_school = user['profile'].get('school')

        # 2. 直接读取课程数据库
        courses_db = get_db_data("courses.json")
        
        # 3. 在前端逻辑中查找对应的 course_map
        target_roadmap = []
        
        # 深入 JSON 树状结构查找
        for college in courses_db.get("学院列表", []):
            if college.get("学院名称") == user_school:
                for major_item in college.get("专业列表", []):
                    if major_item.get("专业名称") == user_major:
                        # 🚩 核心逻辑：直接读取后端已经生成好的 course_map 字段
                        target_roadmap = major_item.get("course_map", [])
                        break
        
        # 4. 渲染地图
        if target_roadmap:
            # 确保按学期排序
            target_roadmap.sort(key=lambda x: x.get("semester", 1))

            # 遍历 1-8 学期展示
            for s in range(1, 9):
                s_courses = [c for c in target_roadmap if int(c.get('semester', 0)) == s]
                
                if s_courses:
                    st.markdown(f"#### 📅 第 {s} 学期")
                    # 动态创建列，让课程卡片横向排列
                    cols = st.columns(len(s_courses))
                    for i, c in enumerate(s_courses):
                        # 使用 success 样式的绿色小卡片
                        cols[i].success(f"**{c['name']}**  \n({c.get('credits', 0)} 学分)")
                    st.divider() # 学期见分割线
        else:
            st.warning("⚠️ 暂无地图数据。请确保管理员已为该专业生成 course_map。")

    # --- 🚩 TAB 5: 路径匹配与复盘 (深度美化版) ---
    with tab_match:
        st.subheader("🏁 我的成长复盘")
        path_review = user.get("path_review", {})
        
        c_p1, c_p2 = st.columns(2)
        with c_p1: st.info(f"💬 我的评价内容：\n\n{path_review.get('content', '暂未填写')}")
        with c_p2:
            st.write(f"❤️ 累计获得点赞：**{path_review.get('like_count', 0)}**")
            st.write(f"🏆 当前影响力排名：**No.{path_review.get('current_rank', '-')}**")

        # 2. 修改评价的部分
        with st.expander("✍️ 撰写/修改我的全路径评价"):
            # 🚩 关键修改：key 绑定版本号，且不设置固定的 value
            new_comment_text = st.text_area(
                "分享你的避坑经验或保研/就业心得：", 
                placeholder="在此输入新的内容",
                height=150, 
                key=f"my_comment_box_{st.session_state.comment_version}" 
            )
            
            if st.button("提交评价"):
                if new_comment_text:
                    if record_comment(st.session_state.user_id, new_comment_text):
                        # 🚩 成功后版本号+1，强制清空输入框
                        st.session_state.comment_version += 1
                        st.success("评价已存入！正在重新计算排名...")
                        generate_comment_rank_list()
                        st.rerun()
                else:
                    st.warning("内容不能为空")

        st.divider()
        st.subheader("🤝 AI 路径匹配")
        
        if st.button("🔍 开始匹配相似路径", type="primary"):
            with st.spinner("AI 正在分析路径..."):
                st.session_state.matched_uids = stream_conversation_for_match(st.session_state.user_id)
        
        # --- 修复 2: 完整路径可视化展示 ---
        if st.session_state.matched_uids:
            # 预加载所有数据库以便获取 description/abstract
            c_db = get_db_data("courses.json")
            r_db = get_db_data("research.json")
            ct_db = get_db_data("contests.json")

            # 建立描述字典
            desc_lookup = {}
            # 解析科研 abstract
            for col in r_db.get("学院列表", []):
                for m in col.get("专业列表", []):
                    for r in m.get("科研列表", []): desc_lookup[r['name']] = r.get('abstract', "暂无简介")
            # 解析竞赛 description
            for col in ct_db.get("学院列表", []):
                for m in col.get("专业列表", []):
                    for ct in m.get("竞赛列表", []): desc_lookup[ct['name']] = ct.get('description', "暂无简介")

            for m_uid in st.session_state.matched_uids:
                peer = all_users.get(m_uid)
                if not peer: continue
                
                with st.container(border=True):
                    header_col, like_col = st.columns([5, 1])
                    with header_col:
                        st.markdown(f"### 🎯 目标：{peer['profile']['target']} 专业：{peer['profile']['major']}")
                    with like_col:
                        if st.button(f"👍 {peer.get('path_review', {}).get('like_count', 0)}", key=f"like_{m_uid}"):
                            if add_like(m_uid): st.rerun()

                    st.write(f"💬 **复盘经验：** {peer.get('path_review', {}).get('content', '该用户暂未发表评价')}")
                    
                    # --- 路径可视化展示 ---
                    path_col1, path_col2, path_col3 = st.columns(3)
                    
                    with path_col1:
                        st.write("📘 **修读课程 (按学期)**")
                        # 课程按学期分组
                        course_groups = defaultdict(list)
                        for c in peer['academic_progress'].get('completed_courses', []):
                            course_groups[c['semester']].append(c['name'])
                        
                        # 按学期 1-8 循环
                        for sem in sorted(course_groups.keys()):
                            with st.popover(f"第 {sem} 学期课程"):
                                st.write(f"**该学期修读详情：**")
                                for cname in course_groups[sem]:
                                    st.write(f"• {cname}")

                    with path_col2:
                        st.write("🏆 **参与竞赛**")
                        for ct in peer['academic_progress'].get('competitions_done', []):
                            with st.popover(f"Sem {ct['complete_semester']}: {ct['name']}"):
                                st.write(f"**获得奖项：** {ct.get('award', '未填写')}")
                                st.info(desc_lookup.get(ct['name'], "暂无竞赛描述"))

                    with path_col3:
                        st.write("🧪 **科研项目**")
                        for rs in peer['academic_progress'].get('research_done', []):
                            with st.popover(f"Sem {rs['complete_semester']}: {rs['name']}"):
                                st.write("**研究内容简介：**")
                                st.info(desc_lookup.get(rs['name'], "暂无项目详情"))


    # --- 🚩 新增 TAB 6: 荣誉排行榜 ---
    with tab_rank:
        st.subheader("🏆 全校路径贡献榜 (Top 30)")
        st.caption("以下是根据大家点赞选出的最具有参考价值的复盘经验。")
        # 实时生成排名
        rank_list = generate_comment_rank_list()
        if rank_list:
            # 只取前30名
            df_rank = pd.DataFrame(rank_list[:30])
            df_rank.columns = ["姓名", "点赞数", "当前排名"]
            st.dataframe(df_rank, use_container_width=True, hide_index=True)
        else:
            st.info("榜单尚未生成，快去发表你的评价吧！")

# --- 6. 推荐页面 (保持原有流式对话逻辑) ---
elif st.session_state.step == "recommendation":
    # 同样需要获取最新的用户信息来展示问候语
    all_users = get_db_data("users.json")
    user = all_users.get(st.session_state.user_id)

    st.title("🤖 AI 智能学业规划导师")
    
    # 🚩 新增：个性化问候与功能指引
    st.markdown(f"#### 您好，{user['profile']['name']}！")
    st.markdown(f"""
    我是您的专属学业数字助手。我已经调取了您的**专业培养方案、当前绩点、已点亮的技能树**以及您设定的**{user['profile']['target']}**目标。
    
    您可以向我咨询任何关于选课、竞赛、科研或职业发展的疑问，我会根据您的个人实际情况给出量身定制的规划建议。
    """)
    st.divider()

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
            status_placeholder = st.empty()
            status_placeholder.info("🔍 系统正在根据您的情况做出判断，请稍等...")

            try:
                response_generator = stream_conversation_for_plan(st.session_state.user_id, prompt)
                
                # ✅ 修复：使用列表作为 flag，避免使用 nonlocal 报错
                container = {"first_chunk_received": False}
                
                def wrapped_generator():
                    for chunk in response_generator:
                        if not container["first_chunk_received"]:
                            status_placeholder.empty()  # 收到第一个字，清空“请稍等”
                            container["first_chunk_received"] = True
                        yield chunk

                # 使用 st.write_stream 渲染
                full_response = st.write_stream(wrapped_generator())
                
                # 3. 将完整回复存入历史记录
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            except Exception as e:
                status_placeholder.empty()
                st.error(f"对话出错：{str(e)}")