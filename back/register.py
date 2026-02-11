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
                    # 获取该专业的必修课类别列表
                    required_categories = major.get("必修课类别列表", [])
                    
                    for course in major.get("课程列表", []):
                        # 只将在必修课类别列表中的课程添加到规划中
                        if course.get("category") in required_categories:
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
    """
    更新用户进度并重新计算分值
    逻辑：
    1. 课程 -> 仅加在 knowledge (技能树)
    2. 科研/竞赛 -> 仅加在 skills (雷达图)
    """
    users_all = get_db_data("users.json")
    user = users_all.get(user_id)
    if not user: return False

    try:
        # 1. 逻辑去重（确保同一项目不重复出现在列表中）
        def deduplicate(data_list):
            unique_data = {}
            for item in data_list:
                unique_data[item['name']] = item
            return list(unique_data.values())

        user["academic_progress"]["completed_courses"] = deduplicate(payload.get("courses", []))
        user["academic_progress"]["competitions_done"] = deduplicate(payload.get("competitions", []))
        user["academic_progress"]["research_done"] = deduplicate(payload.get("research", []))

        # 2. 准备查找字典 (扁平化所有数据库方便查询)
        def build_lookup(db_name, list_key):
            lookup = {}
            db_content = get_db_data(db_name)
            for college in db_content.get("学院列表", []):
                for major in college.get("专业列表", []):
                    for item in major.get(list_key, []):
                        lookup[item["name"]] = item
            return lookup

        course_lookup = build_lookup("courses.json", "课程列表")
        research_lookup = build_lookup("research.json", "科研列表")
        contest_lookup = build_lookup("contests.json", "竞赛列表")

        # 3. 初始化/清零 知识点和能力分数，准备重算
        for k in user["knowledge"]: user["knowledge"][k] = 0.0
        for s in user["skills"]: user["skills"][s] = 0.0
        
        # 4. --- 计算课程贡献 (仅 Knowledge) ---
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
                
                # 更新知识树分数：维度分 * 学分 * 绩点
                if "knowledge" in info:
                    for kd, base in info["knowledge"].items():
                        if kd in user["knowledge"]:
                            user["knowledge"][kd] += round(base * creds * gpa, 2)

        # 5. --- 计算科研贡献 (仅 Skills) ---
        # 逻辑：直接累加科研库中定义的 skills 基础分
        for r_done in user["academic_progress"]["research_done"]:
            name = r_done["name"]
            if name in research_lookup:
                info = research_lookup[name]
                if "skills" in info:
                    for sd, val in info["skills"].items():
                        if sd in user["skills"]:
                            user["skills"][sd] += float(val)

        # 6. --- 计算竞赛贡献 (仅 Skills) ---
        # 逻辑：直接累加竞赛库中定义的 skills 基础分 (忽略获奖情况)
        for ct_done in user["academic_progress"]["competitions_done"]:
            name = ct_done["name"]
            if name in contest_lookup:
                info = contest_lookup[name]
                if "skills" in info:
                    for sd, val in info["skills"].items():
                        if sd in user["skills"]:
                            user["skills"][sd] += float(val)

        # 7. 更新汇总统计字段 (GPA & 总学分)
        user["total_credits"] = total_credits
        user["average_grades"] = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0.0

        # 8. 保存回 JSON
        users_all[user_id] = user
        with open(os.path.join(DB_DIR, "users.json"), "w", encoding="utf-8") as f:
            json.dump(users_all, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Update Error: {e}")
        return False