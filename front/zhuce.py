import streamlit as st
import requests  # 用于后续给后端发请求
import json
import os
# --- 页面配置 ---
st.set_page_config(page_title="智航 - AI 学业导航系统", layout="centered")

# --- 初始化 Session State (用于维护页面状态) ---
if 'step' not in st.session_state:
    st.session_state.step = "registration"  # 初始状态是注册页
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- 模拟后端对接函数 ---
def register_user_to_backend(data):
    """
    这里是给后端同学 A 预留的接口位置。
    目前我们可以先模拟成功，以后改为 requests.post("http://localhost:8000/register", json=data)
    """
    # 模拟后端处理
    #return True, "注册成功！"
    """
    实现逻辑：将前端表单数据按照约定的格式初始化并存入 users.json
    """
    # 获取当前脚本（zhuce.py）所在的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 拼接出 databases/users.json 的完整路径
    db_path = os.path.join(script_dir, "..", "databases", "users.json")
    
    # 1. 生成唯一标识码 (user_ + 10位学号)
    user_id = f"user_{str(data['student_id']).zfill(10)}"
    
    # 2. 构建完整的初始化字典 (包含所有空字段)
    new_user_entry = {
        "profile": {
            "name": data['name'],
            "enrollment_year": int(data['enrollment_year']),
            "school": data['school'],
            "major": data['major'],
            "target": data['target']
        },
        "academic_progress": {
            "current_semester": int(data['current_semester']),
            "completed_courses": [],
            "research_done": [],
            "competitions_done": []
        },
        "remaining_tasks": {
            "must_required_courses": [],
            "credit_gaps": []
        },
        "path_review": {
            "is_public": False,
            "content": "",
            "citation_count": 0,
            "current_rank": 0
        },
        "knowledge": { k: 0 for k in ["数学基础", "编程语言、算法与软件工程", "计算机系统与网络", "数据与智能", "网络安全与信息保护"] },
        "skills": { s: 0 for s in ["系统化思维", "形式化逻辑与数学迁移", "工具化与自动化本能", "信息检索与数据处理", "异常处理与边界意识"] }
    }

    try:
        # 3. 读取现有数据库内容
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                db_data = json.load(f)
        else:
            db_data = {}

        # 4. 插入新用户并回写
        db_data[user_id] = new_user_entry
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
        
        return True, f"注册成功！用户ID: {user_id}"
    
    except Exception as e:
        return False, f"注册失败，错误信息: {str(e)}"

# --- 1. 注册页面 ---
if st.session_state.step == "registration":
    st.title("🚀 欢迎开启您的 AI 学业导航")
    st.subheader("请填写基本信息以初始化您的学业画像")

    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("姓名", placeholder="请输入真实姓名")
            student_id = st.text_input("学工号", placeholder="例如：2023000001")
            enrollment_year = st.selectbox("入学年份", [2022, 2023, 2024, 2025], index=3)
        
        with col2:
            school = st.selectbox("学院", ["信息学院", "高瓴人工智能学院", "其他"])
            major = st.text_input("专业", placeholder="如：计算机科学与技术")
            target = st.selectbox("最终目标", ["保研", "出国深造", "本科就业", "考研", "不确定"])

        current_semester = st.slider("当前所处学期", 1, 8, 1)
        
        submit_button = st.form_submit_button("完成注册")

        if submit_button:
            if name and student_id and major:
                # 构造要发给后端的数据
                user_data = {
                    "name": name,
                    "student_id": student_id,
                    "enrollment_year": enrollment_year,
                    "school": school,
                    "major": major,
                    "target": target,
                    "current_semester": current_semester
                }
                
                # 调用后端接口
                success, message = register_user_to_backend(user_data)
                
                if success:
                    st.session_state.user_info = user_data
                    st.success(message)
                    # 根据学期决定下一步状态
                    if current_semester == 1:
                        st.session_state.step = "new_student_map"
                    else:
                        st.session_state.step = "input_history"
                    
                    st.rerun() # 立即刷新页面进入下一步
            else:
                st.error("请完整填写带 * 的必填信息")

# --- 2. 下一步：新生必修地图 (占位) ---
elif st.session_state.step == "new_student_map":
    st.title(f"📍 你好，{st.session_state.user_info['name']}！")
    st.info("检测到你处于第 1 学期，系统已为你生成基础必修课程地图。")
    st.write("这里将展示从 PDF 解析出来的四年必修课时间轴...")
    if st.button("返回修改注册信息"):
        st.session_state.step = "registration"
        st.rerun()

# --- 3. 下一步：老生输入历史 (占位) ---
elif st.session_state.step == "input_history":
    st.title(f"🔍 欢迎回来，{st.session_state.user_info['name']}！")
    st.info(f"检测到你处于第 {st.session_state.user_info['current_semester']} 学期，请录入你已完成的修读记录。")
    st.write("这里将提供一个表单，让你选择已完成的课程、科研和竞赛...")
    if st.button("返回修改注册信息"):
        st.session_state.step = "registration"
        st.rerun()