import json
import os

# 定义数据库目录（相对于 logic.py 的位置）
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "databases")

def register_user(data):
    """
    接收前端传来的字典，初始化并存入 users.json
    """
    db_path = os.path.join(DB_DIR, "users.json")
    
    # 1. 生成 ID
    user_id = f"user_{str(data['student_id']).zfill(10)}"
    
    # 2. 构建完整的初始化结构
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
        "path_review": {"is_public": False, "content": "", "citation_count": 0, "current_rank": 0},
        "knowledge": { k: 0 for k in ["数学基础", "编程语言、算法与软件工程", "计算机系统与网络", "数据与智能", "网络安全与信息保护"] },
        "skills": { s: 0 for s in ["系统化思维", "形式化逻辑与数学迁移", "工具化与自动化本能", "信息检索与数据处理", "异常处理与边界意识"] }
    }

    try:
        # 3. 读取并写入
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                db_data = json.load(f)
        else:
            db_data = {}

        # 如果需要查重，A 同学可以在这里加：
        if user_id in db_data: return False, "学号已注册"

        db_data[user_id] = new_user_entry
        
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
            
        return True, user_id
    except Exception as e:
        return False, str(e)

def get_mandatory_roadmap(user_id):
    """
    任务：
    1. 读取 users.json，找到 user_id 对应的 major。
    2. 读取 courses.json，筛选该专业的必修课。
    3. 将结果写回 users.json 的 must_required_courses 字段。
    4. 返回列表: [{"name": "数分I", "semester": 1, "credits": 5}, ...]
    """
    # 定义文件路径
    users_path = os.path.join(DB_DIR, "users.json")
    courses_path = os.path.join(DB_DIR, "courses.json")

    try:
        # 读取 users.json
        with open(users_path, "r", encoding="utf-8") as f:
            users_data = json.load(f)

        if user_id not in users_data:
            raise ValueError("用户ID不存在")

        # 获取用户的专业
        user_major = users_data[user_id]["profile"]["major"]

        # 读取 courses.json
        with open(courses_path, "r", encoding="utf-8") as f:
            courses_data = json.load(f)

        # 筛选该专业的必修课
        mandatory_courses = []
        for college in courses_data["学院列表"]:
            for major in college["专业列表"]:
                if major["专业名称"] == user_major:
                    for course in major["课程列表"]:
                        mandatory_courses.append({
                            "name": course["name"],
                            "semester": course["standard_semester"],
                            "credits": course["credits"]
                        })

        # 按学期排序
        mandatory_courses.sort(key=lambda x: x["semester"])

        # 写回 users.json 的 must_required_courses 字段
        users_data[user_id]["remaining_tasks"]["must_required_courses"] = mandatory_courses
        with open(users_path, "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)

        # 返回结果
        return mandatory_courses

    except Exception as e:
        print(f"Error: {e}")
        return []

def get_selection_options(user_id):
    """
    任务：
    根据用户的id，到user.json里面找到用户的学院和专业，
    从 courses.json, research.json, contests.json 提取所有从属该学院下专业的名称。
    返回: {"courses": ["Python", "微积分"], "research": ["AI实验室"], "contests": ["ACM"]}
    """
    # 定义文件路径
    users_path = os.path.join(DB_DIR, "users.json")
    courses_path = os.path.join(DB_DIR, "courses.json")
    research_path = os.path.join(DB_DIR, "research.json")
    contests_path = os.path.join(DB_DIR, "contests.json")

    try:
        # 读取 users.json
        with open(users_path, "r", encoding="utf-8") as f:
            users_data = json.load(f)

        if user_id not in users_data:
            raise ValueError("用户ID不存在")

        # 获取用户的学院和专业
        user_school = users_data[user_id]["profile"]["school"]
        user_major = users_data[user_id]["profile"]["major"]

        # 初始化选项
        options = {"courses": [], "research": [], "contests": []}

        # 读取 courses.json
        with open(courses_path, "r", encoding="utf-8") as f:
            courses_data = json.load(f)

        for college in courses_data["学院列表"]:
            if college["学院名称"] == user_school:
                for major in college["专业列表"]:
                    if major["专业名称"] == user_major:
                        options["courses"] = [course["name"] for course in major["课程列表"]]

        # 读取 research.json
        with open(research_path, "r", encoding="utf-8") as f:
            research_data = json.load(f)

        for college in research_data["学院列表"]:
            if college["学院名称"] == user_school:
                for major in college["专业列表"]:
                    if major["专业名称"] == user_major:
                        options["research"] = [research["name"] for research in major["科研列表"]]

        # 读取 contests.json
        with open(contests_path, "r", encoding="utf-8") as f:
            contests_data = json.load(f)

        for college in contests_data["学院列表"]:
            if college["学院名称"] == user_school:
                for major in college["专业列表"]:
                    if major["专业名称"] == user_major:
                        options["contests"] = [contest["name"] for contest in major["竞赛列表"]]

        return options

    except Exception as e:
        print(f"Error: {e}")
        return {"courses": [], "research": [], "contests": []}

def update_user_progress(user_id, completed_data):
    """
    任务：
    1. 接收前端传来的已完成列表。
    2. 更新 users.json 的 academic_progress。
    3. 核心：根据已完成课程的标签，累加用户的 knowledge 和 skills 分数（点亮技能树）。
    4. 计算剩余学分缺口 (credit_gaps)。
    """
    # 定义文件路径
    users_path = os.path.join(DB_DIR, "users.json")
    courses_path = os.path.join(DB_DIR, "courses.json")

    try:
        # 读取 users.json
        with open(users_path, "r", encoding="utf-8") as f:
            users_data = json.load(f)

        if user_id not in users_data:
            raise ValueError("用户ID不存在")

        user_data = users_data[user_id]

        # 更新 academic_progress
        user_data["academic_progress"]["completed_courses"].extend(completed_data.get("courses", []))
        user_data["academic_progress"]["research_done"].extend(completed_data.get("research", []))
        user_data["academic_progress"]["competitions_done"].extend(completed_data.get("contests", []))

        # 读取 courses.json
        with open(courses_path, "r", encoding="utf-8") as f:
            courses_data = json.load(f)

        # 累加 knowledge 和 skills 分数
        for course_name in completed_data.get("courses", []):
            for college in courses_data["学院列表"]:
                for major in college["专业列表"]:
                    for course in major["课程列表"]:
                        if course["name"] == course_name:
                            for knowledge, points in course["knowledge"].items():
                                user_data["knowledge"][knowledge] += points

        # 计算剩余学分缺口
        total_credits = sum(course["credits"] for course in user_data["academic_progress"]["completed_courses"])
        required_credits = 160  # 假设总学分要求为 160
        credit_gaps = required_credits - total_credits

        user_data["remaining_tasks"]["credit_gaps"] = credit_gaps

        # 写回 users.json
        users_data[user_id] = user_data
        with open(users_path, "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


