import json
import os

def record_comment(user_id, comment):
    """
    Record a comment for a user in the users.json database.

    Args:
        user_id (str): The ID of the user to record the comment for.
        comment (str): The comment content to store.

    Returns:
        bool: True if the comment was successfully recorded, False otherwise.
    """
    base_dir = os.path.dirname(__file__)
    users_path = os.path.join(base_dir, '../databases/users.json')

    try:
        # Load the users database
        with open(users_path, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"users.json file not found at {users_path}.")
    except json.JSONDecodeError:
        raise ValueError("Error decoding users.json file.")

    # Find the user by user_id
    if isinstance(users, dict):
        user_info = users.get(user_id)
    else:
        user_info = next((user for user in users if user.get("id") == user_id), None)

    if not user_info:
        raise ValueError(f"User with ID {user_id} not found in users.json.")

    # Update the path_review content field
    if "path_review" not in user_info:
        user_info["path_review"] = {
            "is_public": False,
            "content": comment,
            "like_count": 0,
            "current_rank": 0
        }
    else:
        user_info["path_review"]["content"] = comment

    # Save the updated users database back to file
    try:
        with open(users_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        raise IOError(f"Error writing to users.json: {e}")

def add_like(target_user_id):
    """
    Add a like to a user's path review.

    Args:
        target_user_id (str): The ID of the user to add a like for.

    Returns:
        bool: True if the like was successfully added, False otherwise.
    """
    base_dir = os.path.dirname(__file__)
    users_path = os.path.join(base_dir, '../databases/users.json')

    try:
        # Load the users database
        with open(users_path, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"users.json file not found at {users_path}.")
    except json.JSONDecodeError:
        raise ValueError("Error decoding users.json file.")

    if target_user_id not in users:
        return False

    # Ensure path_review structure is complete
    if "path_review" not in users[target_user_id]:
        users[target_user_id]["path_review"] = {
            "is_public": False,
            "content": "",
            "like_count": 0,
            "current_rank": 0
        }

    # Increment like_count
    users[target_user_id]["path_review"]["like_count"] += 1

    # Save the updated users database back to file
    try:
        with open(users_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        raise IOError(f"Error writing to users.json: {e}")


# if __name__ == "__main__":
#     # Example usage
#     user_id = "user_2023000001"
#     comment = "This is a sample learning path review comment."
    
#     try:
#         success = record_comment(user_id, comment)
#         if success:
#             print(f"Comment recorded successfully for user {user_id}")
#     except Exception as e:
#         print(f"Error: {e}")