import json
import os

# 定义数据库目录（相对于 logic.py 的位置）
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "databases")

def register_user(data):
    """
    接收前端传来的字典，初始化并存入 users.json
    根据其学院和专业，初始化 must_required_courses 为空列表，等待后续填充。
    根据其学院和专业，初始化 knowledge 和 skills 字段信息，并赋予零分状态。
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

    # 根据学院和专业动态生成 knowledge 和 skills 标签
    knowledge_tags = []
    skills_tags = []

    # 定义文件路径
    tags_path = os.path.join(DB_DIR, "tags.json")

    # 读取 tags.json
    with open(tags_path, "r", encoding="utf-8") as f:
        tags_data = json.load(f)

    # 根据学院和专业筛选标签
    for tag in tags_data:
        for college in tag["学院列表"]:
            if college["学院名称"] == data["school"]:
                major_tags = college["专业列表"].get(data["major"], [])
                if tag["tag"] == "knowledge":
                    knowledge_tags = {k: 0 for k in major_tags}
                elif tag["tag"] == "skills":
                    skills_tags = {s: 0 for s in major_tags}

    # 更新 new_user_entry
    new_user_entry["knowledge"] = knowledge_tags
    new_user_entry["skills"] = skills_tags

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

def get_db_data(filename):
    path = os.path.join(DB_DIR, filename)
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_selection_options(user_id):
    users_data = get_db_data("users.json")
    user = users_data.get(user_id)
    if not user: return {"courses": [], "research": [], "contests": {}, "contest_list": []}
    
    school = user["profile"]["school"]
    major_name = user["profile"]["major"]
    
    # 结果容器：contest_awards 存名称到奖项的映射
    res = {"courses": [], "research": [], "contest_awards": {}, "contest_list": []}
    
    # 1. 获取课程
    courses_data = get_db_data("courses.json")
    for college in courses_data.get("学院列表", []):
        if college["学院名称"] == school:
            for major in college.get("专业列表", []):
                if major["专业名称"] == major_name:
                    res["courses"] = [c["name"] for c in major.get("课程列表", [])]

    # 2. 获取科研
    research_data = get_db_data("research.json")
    for college in research_data.get("学院列表", []):
        if college["学院名称"] == school:
            for major in college.get("专业列表", []):
                if major["专业名称"] == major_name:
                    res["research"] = [r["name"] for r in major.get("科研列表", [])]

    # 3. 获取竞赛及其奖项
    contests_data = get_db_data("contests.json")
    for college in contests_data.get("学院列表", []):
        if college["学院名称"] == school:
            for major in college.get("专业列表", []):
                if major["专业名称"] == major_name:
                    for ct in major.get("竞赛列表", []):
                        name = ct["name"]
                        res["contest_list"].append(name)
                        # 将奖项列表存入字典，供前端查询
                        res["contest_awards"][name] = ct.get("potential_awards", ["参与奖"])
            
    return res

def update_user_progress(user_id, completed_payload):
    """
    修正核心逻辑：此时 completed_payload['courses'] 里面是字典列表
    """
    users_data = get_db_data("users.json")
    user = users_data.get(user_id)
    if not user: return False

    try:
        # 更新数据库
        user["academic_progress"]["completed_courses"] = completed_payload["courses"]
        user["academic_progress"]["research_done"] = completed_payload["research"]
        user["academic_progress"]["competitions_done"] = completed_payload["competitions"]

        # 计算学分与技能累加（需要查找课程详情）
        courses_data = get_db_data("courses.json")
        course_lookup = {}
        for college in courses_data.get("学院列表", []):
            for major in college.get("专业列表", []):
                for c in major.get("课程列表", []):
                    course_lookup[c["name"]] = c

        total_credits = 0
        # 重置当前分数
        for k in user["knowledge"]: user["knowledge"][k] = 0
        for s in user["skills"]: user["skills"][s] = 0

        # 处理课程带来的增益
        for c_done in completed_payload["courses"]:
            c_name = c_done["name"]
            if c_name in course_lookup:
                info = course_lookup[c_name]
                total_credits += info.get("credits", 0)
                # 累加知识点
                for k_tag, val in info.get("knowledge", {}).items():
                    if k_tag in user["knowledge"]:
                        user["knowledge"][k_tag] += val
                # 累加技能（如果有）
                for s_tag, val in info.get("skills", {}).items():
                    if s_tag in user["skills"]:
                        user["skills"][s_tag] += val

        # 更新学分缺口
        user["remaining_tasks"]["credit_gaps"] = [
            {"category": "总学分完成情况", "missing_credits": max(0, 155 - total_credits)}
        ]

        users_data[user_id] = user
        with open(os.path.join(DB_DIR, "users.json"), "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Update Error: {e}")
        return False

