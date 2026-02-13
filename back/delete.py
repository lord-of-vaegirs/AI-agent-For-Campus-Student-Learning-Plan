import json
import os


DB_DIR = os.path.join(os.path.dirname(__file__), "..", "databases")


def delete_user(user_id):
    db_path = os.path.join(DB_DIR, "users.json")
    if not os.path.exists(db_path):
        return False

    with open(db_path, "r", encoding="utf-8") as f:
        try:
            users = json.load(f)
        except Exception:
            return False

    if user_id not in users:
        return False

    users.pop(user_id, None)
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return True

# if __name__ == "__main__":
#     test_user_id = "user_xxxxx"
#     if delete_user(test_user_id):
#         print(f"User {test_user_id} deleted successfully.")
#     else:
#         print(f"Failed to delete user {test_user_id}.")