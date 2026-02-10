import json
import os

# 定义数据库目录
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "databases")
def login_user(student_id):
    """
    登录验证：根据学号检查用户是否存在
    """
    users_all = get_db_data("users.json")
    user_id = f"user_{str(student_id).zfill(10)}"
    
    if user_id in users_all:
        return True, user_id, users_all[user_id]
    return False, "学号未注册", None
def get_db_data(filename):
    """读取JSON数据，返回原始字典"""
    path = os.path.join(DB_DIR, filename)
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except: return {}

def register_user(data):
    """注册用户并初始化结构"""
    db_path = os.path.join(DB_DIR, "users.json")
    user_id = f"user_{str(data['student_id']).zfill(10)}"
    
    new_user = {
        "profile": {
            "name": data['name'], 
            "enrollment_year": int(data['enrollment_year']),
            "school": data['school'], 
            "major": data['major'], 
            "target": data['target']
        },
        "academic_progress": {
            "current_semester": int(data['current_semester']),
            "completed_courses": [], "research_done": [], "competitions_done": []
        },
        "remaining_tasks": {"must_required_courses": [], "credit_gaps": []},
        "path_review": {"is_public": False, "content": "", "citation_count": 0, "current_rank": 0},
        "knowledge": {}, "skills": {},
        "total_credits": 0.0,
        "average_grades": 0.0
    }

    # 1. 尝试从 tags.json 初始化标签 (假设 tags.json 是个列表)
    tags_all = get_db_data("tags.json")
    if isinstance(tags_all, list):
        for item in tags_all:
            for college in item.get("学院列表", []):
                if college.get("学院名称") == data["school"]:
                    major_tags = college.get("专业列表", {}).get(data["major"], [])
                    tag_key = item.get("tag") # knowledge 或 skills
                    if tag_key in new_user:
                        new_user[tag_key] = {t: 0.0 for t in major_tags}

    try:
        users = get_db_data("users.json")
        if not isinstance(users, dict): users = {}
        if user_id in users: return False, "学号已注册"
        
        users[user_id] = new_user
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True, user_id
    except Exception as e:
        return False, str(e)

def get_mandatory_roadmap(user_id):
    """根据专业获取必修课表"""
    users = get_db_data("users.json")
    user = users.get(user_id)
    if not user: return []
    
    target_school = user["profile"]["school"]
    target_major = user["profile"]["major"]
    
    courses_data = get_db_data("courses.json")
    roadmap = []
    
    # 正确遍历你提供的字典嵌套结构
    for college in courses_data.get("学院列表", []):
        if college.get("学院名称") == target_school:
            for major in college.get("专业列表", []):
                if major.get("专业名称") == target_major:
                    for course in major.get("课程列表", []):
                        # 将必修课提取到规划中
                        roadmap.append({
                            "name": course["name"],
                            "semester": course.get("standard_semester", 1),
                            "credits": course.get("credits", 0)
                        })
    
    roadmap.sort(key=lambda x: x["semester"])
    # 同步回用户数据库
    user["remaining_tasks"]["must_required_courses"] = roadmap
    users[user_id] = user
    with open(os.path.join(DB_DIR, "users.json"), "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
        
    return roadmap

def get_selection_options(user_id):
    """获取该专业下可选的课程、科研和竞赛"""
    users = get_db_data("users.json")
    user = users.get(user_id)
    if not user: return {"courses": [], "research": [], "contest_list": [], "contest_awards": {}}
    
    school = user["profile"]["school"]
    major_name = user["profile"]["major"]
    res = {"courses": [], "research": [], "contest_list": [], "contest_awards": {}}
    
    # 1. 提取课程
    c_data = get_db_data("courses.json")
    for college in c_data.get("学院列表", []):
        if college.get("学院名称") == school:
            for m in college.get("专业列表", []):
                if m.get("专业名称") == major_name:
                    res["courses"] = [c["name"] for c in m.get("课程列表", [])]

    # 2. 提取科研
    r_data = get_db_data("research.json")
    for college in r_data.get("学院列表", []):
        if college.get("学院名称") == school:
            for m in college.get("专业列表", []):
                if m.get("专业名称") == major_name:
                    res["research"] = [r["name"] for r in m.get("科研列表", [])]

    # 3. 提取竞赛
    ct_data = get_db_data("contests.json")
    for college in ct_data.get("学院列表", []):
        if college.get("学院名称") == school:
            for m in college.get("专业列表", []):
                if m.get("专业名称") == major_name:
                    for ct in m.get("竞赛列表", []):
                        res["contest_list"].append(ct["name"])
                        res["contest_awards"][ct["name"]] = ct.get("potential_awards", ["参与奖"])
    return res

def update_user_progress(user_id, payload):
    users_all = get_db_data("users.json")
    user = users_all.get(user_id)
    if not user: return False

    try:
        # --- 核心修改：逻辑去重 ---
        # 使用字典的 Key 特性，确保同一个名字的课程/竞赛只保留一个最新对象
        def deduplicate(data_list):
            unique_data = {}
            for item in data_list:
                unique_data[item['name']] = item
            return list(unique_data.values())

        user["academic_progress"]["completed_courses"] = deduplicate(payload.get("courses", []))
        user["academic_progress"]["competitions_done"] = deduplicate(payload.get("competitions", []))
        user["academic_progress"]["research_done"] = deduplicate(payload.get("research", []))

        # --- 重新计算分值 (逻辑同之前) ---
        course_lookup = {}
        c_all = get_db_data("courses.json")
        for col in c_all.get("学院列表", []):
            for m in col.get("专业列表", []):
                for c in m.get("课程列表", []):
                    course_lookup[c["name"]] = c

        # 重置分数
        for k in user["knowledge"]: user["knowledge"][k] = 0.0
        for s in user["skills"]: user["skills"][s] = 0.0
        total_creds = 0.0

        for c_done in user["academic_progress"]["completed_courses"]:
            name = c_done["name"]
            gpa = float(c_done.get("grade", 0))
            if name in course_lookup:
                info = course_lookup[name]
                creds = float(info.get("credits", 0))
                total_creds += creds
                
                # 重新计算 Knowledge
                for kd, base in info.get("knowledge", {}).items():
                    if kd in user["knowledge"]:
                        user["knowledge"][kd] += round(base * creds * gpa, 2)
                # 重新计算 Skills
                for sd, base in info.get("skills", {}).items():
                    if sd in user["skills"]:
                        user["skills"][sd] += round(base * creds * gpa, 2)

        # --- 计算总学分和平均绩点 ---
        total_credits = 0.0
        total_grade_points = 0.0

        for c_done in user["academic_progress"]["completed_courses"]:
            name = c_done["name"]
            gpa = float(c_done.get("grade", 0))
            if name in course_lookup:
                info = course_lookup[name]
                creds = float(info.get("credits", 0))
                total_credits += creds
                total_grade_points += creds * gpa

        # 计算平均绩点
        average_grades = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0.0

        # 更新用户的总学分和平均绩点
        user["total_credits"] = total_credits
        user["average_grades"] = average_grades

        # 保存回 JSON
        users_all[user_id] = user
        with open(os.path.join(DB_DIR, "users.json"), "w", encoding="utf-8") as f:
            json.dump(users_all, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False