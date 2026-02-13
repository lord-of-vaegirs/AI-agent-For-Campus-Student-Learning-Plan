import json
import os
from datetime import datetime, timedelta, timezone

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
        "path_review": {"is_public": False, "content": "", "like_count": 0, "current_rank": 0},
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

    # 2. 初始化必修课地图与个性化选修课要求
    courses_data = get_db_data("courses.json")
    for college in courses_data.get("学院列表", []):
        if college.get("学院名称") == data["school"]:
            for major_item in college.get("专业列表", []):
                if major_item.get("专业名称") == data["major"]:
                    new_user["remaining_tasks"]["must_required_courses"] = major_item.get("course_map", [])
                    break

    requirements_data = get_db_data("course_requirement.json")
    for college in requirements_data.get("学院列表", []):
        if college.get("学院名称") == data["school"]:
            for major_item in college.get("专业列表", []):
                if major_item.get("专业名称") == data["major"]:
                    new_user["remaining_tasks"]["credit_gaps"] = major_item.get("个性化选修课课程要求", [])
                    break

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

def get_mandatory_roadmap(major):
    """
    根据专业生成必修课地图并写入 courses.json 的 course_map
    目前该函数只允许开发者使用
    """
    courses_data = get_db_data("courses.json")
    roadmap = []

    for college in courses_data.get("学院列表", []):
        for major_item in college.get("专业列表", []):
            if major_item.get("专业名称") == major:
                required_categories = major_item.get("必修课类别列表", [])

                for course in major_item.get("课程列表", []):
                    if course.get("category") in required_categories:
                        roadmap.append({
                            "name": course.get("name", ""),
                            "semester": course.get("standard_semester", 1),
                            "credits": course.get("credits", 0)
                        })

                roadmap.sort(key=lambda x: x["semester"])
                major_item["course_map"] = roadmap
                break

    with open(os.path.join(DB_DIR, "courses.json"), "w", encoding="utf-8") as f:
        json.dump(courses_data, f, ensure_ascii=False, indent=2)

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

        # 7. 更新 remaining_tasks (必修课与个性化选修课学分缺口)
        if "remaining_tasks" not in user:
            user["remaining_tasks"] = {"must_required_courses": [], "credit_gaps": []}

        # 必修课：已完成且属于必修类别时，从清单中移除
        required_categories = set()
        elective_subcategory_map = {}
        major_name = user.get("profile", {}).get("major")
        school_name = user.get("profile", {}).get("school")
        courses_data = get_db_data("courses.json")
        for college in courses_data.get("学院列表", []):
            if college.get("学院名称") == school_name:
                for major in college.get("专业列表", []):
                    if major.get("专业名称") == major_name:
                        required_categories = set(major.get("必修课类别列表", []))
                        for item in major.get("个性化选修课类别从属", []):
                            parent = item.get("category")
                            for sub in item.get("subcategories", []):
                                elective_subcategory_map[sub] = parent
                        break

        completed_names = {c.get("name") for c in user["academic_progress"].get("completed_courses", []) if c.get("name")}
        must_required = user["remaining_tasks"].get("must_required_courses", [])
        if required_categories and must_required:
            user["remaining_tasks"]["must_required_courses"] = [
                item for item in must_required
                if not (
                    item.get("name") in completed_names
                    and course_lookup.get(item.get("name"), {}).get("category") in required_categories
                )
            ]

        # 个性化选修：按课程类别所属大类扣减缺口学分，最低不小于 0
        credit_gaps = user["remaining_tasks"].get("credit_gaps", [])
        credit_gap_map = {cg.get("category"): cg for cg in credit_gaps if cg.get("category")}

        for c_done in user["academic_progress"].get("completed_courses", []):
            name = c_done.get("name")
            if not name or name not in course_lookup:
                continue
            course_info = course_lookup[name]
            course_category = course_info.get("category")
            parent_category = elective_subcategory_map.get(course_category)
            if not parent_category:
                continue
            gap_item = credit_gap_map.get(parent_category)
            if not gap_item:
                continue
            credits = float(course_info.get("credits", 0))
            gap_item["missing_credits"] = max(0, float(gap_item.get("missing_credits", 0)) - credits)

        user["remaining_tasks"]["credit_gaps"] = list(credit_gap_map.values())

        # 8. 更新汇总统计字段 (GPA & 总学分)
        user["total_credits"] = total_credits
        user["average_grades"] = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0.0

        # 9. 保存回 JSON
        users_all[user_id] = user
        with open(os.path.join(DB_DIR, "users.json"), "w", encoding="utf-8") as f:
            json.dump(users_all, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Update Error: {e}")
        return False
    

def update_current_semester(user_id):
    users_all = get_db_data("users.json")
    user = users_all.get(user_id)
    if not user:
        return False

    enrollment_year = int(user.get("profile", {}).get("enrollment_year", 0))
    if enrollment_year <= 0:
        return False

    now = datetime.now(timezone(timedelta(hours=8)))
    year = now.year
    month = now.month

    if year < enrollment_year:
        current_semester = 1
    elif year == enrollment_year and month == 9:
        current_semester = 1
    else:
        if month in (10, 11, 12, 1, 2, 3):
            period_type = 0  # Oct-Mar
            period_year = year if month >= 10 else year - 1
        else:
            period_type = 1  # Apr-Sep
            period_year = year - 1

        period_index = (period_year - enrollment_year) * 2 + period_type
        current_semester = period_index + 2

    if current_semester < 1:
        current_semester = 1
    elif current_semester > 8:
        current_semester = 8

    if "academic_progress" not in user:
        user["academic_progress"] = {}
    user["academic_progress"]["current_semester"] = int(current_semester)

    users_all[user_id] = user
    with open(os.path.join(DB_DIR, "users.json"), "w", encoding="utf-8") as f:
        json.dump(users_all, f, ensure_ascii=False, indent=2)

    return current_semester

def graduate_warning(user_id):
    pass

# if __name__ == "__main__":
#     get_mandatory_roadmap("计算机科学与技术")
