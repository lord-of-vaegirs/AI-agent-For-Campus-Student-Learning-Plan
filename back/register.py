import json
import os

def initialize_new_user(reg_data, db_path="users.json"):
    """
    reg_data: 来自前端的字典，包含：name, student_id, enrollment_year, school, major, target, current_semester
    """
    # 1. 生成唯一标识码 (user_ + 10位学号)
    # 确保学号是10位字符串，如果前端传的是数字，这里做转换和补齐
    std_id_str = str(reg_data['student_id']).zfill(10)
    user_id = f"user_{std_id_str}"
    
    # 2. 构建完整的初始化字典
    new_user_entry = {
        "profile": {
            "name": reg_data['name'],
            "enrollment_year": int(reg_data['enrollment_year']),
            "school": reg_data['school'],
            "major": reg_data['major'],
            "target": reg_data['target']
        },
        "academic_progress": {
            "current_semester": int(reg_data['current_semester']),
            "completed_courses": [],   # 初始为空
            "research_done": [],        # 初始为空
            "competitions_done": []     # 初始为空
        },
        "remaining_tasks": {
            "must_required_courses": [], # 后续由后端根据培养方案匹配填入
            "credit_gaps": []            # 后续由后端计算填入
        },
        "path_review": {
            "is_public": False,
            "content": "",
            "citation_count": 0,
            "current_rank": 0
        },
        "knowledge": {
            "数学基础": 0,
            "编程语言、算法与软件工程": 0,
            "计算机系统与网络": 0,
            "数据与智能": 0,
            "网络安全与信息保护": 0
        },
        "skills": {
            "系统化思维": 0,
            "形式化逻辑与数学迁移": 0,
            "工具化与自动化本能": 0,
            "信息检索与数据处理": 0,
            "异常处理与边界意识": 0
        }
    }

    # 3. 写入 JSON 文件
    # 读取旧数据
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            try:
                db_data = json.load(f)
            except json.JSONDecodeError:
                db_data = {}
    else:
        db_data = {}

    # 插入新用户并保存
    db_data[user_id] = new_user_entry
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)
    
    return user_id, new_user_entry

if __name__ == "__main__":
    # 测试用例
    registration_data = {
        "name": "李华",
        "student_id": "2023000001",
        "enrollment_year": 2023,
        "school": "信息学院",
        "major": "计算机科学与技术",
        "target": "保研",
        "current_semester": 3
    }
    user_id, user_data = initialize_new_user(registration_data)
    print(f"New user created with ID: {user_id}")
    print(json.dumps(user_data, ensure_ascii=False, indent=2))