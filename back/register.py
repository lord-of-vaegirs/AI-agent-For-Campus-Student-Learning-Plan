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
        # if user_id in db_data: return False, "学号已注册"

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
    return [] # 待填充

def get_selection_options():
    """
    任务：
    从 courses.json, research.json, contests.json 提取所有名称。
    返回: {"courses": ["Python", "微积分"], "research": ["AI实验室"], "contests": ["ACM"]}
    """
    return {"courses":[], "research":[], "contests":[]} # 待填充

def update_user_progress(user_id, completed_data):
    """
    任务：
    1. 接收前端传来的已完成列表。
    2. 更新 users.json 的 academic_progress。
    3. 核心：根据已完成课程的标签，累加用户的 knowledge 和 skills 分数（点亮技能树）。
    4. 计算剩余学分缺口 (credit_gaps)。
    """
    return True # 待填充


