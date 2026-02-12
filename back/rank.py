import json
import os

def generate_comment_rank_list():
    """
    Generate a ranking list of users based on their comment like_count.
    Updates users.json with current_rank and saves the ranking to rank.json.
    
    Returns:
        list: A list of dictionaries with user ranking information in rank.json format.
              Each entry contains: user_name, like_count, current_rank
    """
    base_dir = os.path.dirname(__file__)
    users_path = os.path.join(base_dir, '../databases/users.json')
    rank_path = os.path.join(base_dir, '../databases/rank.json')
    
    try:
        # Load users database
        with open(users_path, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"users.json file not found at {users_path}.")
    except json.JSONDecodeError:
        raise ValueError("Error decoding users.json file.")
    
    # Extract user ranking data
    user_ranking_data = []
    for user_id, user_info in users.items():
        user_name = user_info.get('profile', {}).get('name', 'Unknown')
        like_count = user_info.get('path_review', {}).get('like_count', 0)
        user_ranking_data.append({
            'user_id': user_id,
            'user_name': user_name,
            'like_count': like_count
        })
    
    # Sort by like_count in descending order
    user_ranking_data.sort(key=lambda x: x['like_count'], reverse=True)
    
    # Create the ranking list and update users.json with current_rank
    ranking_list = []
    for rank, user_data in enumerate(user_ranking_data, start=1):
        user_id = user_data['user_id']
        user_name = user_data['user_name']
        like_count = user_data['like_count']
        
        # Update the current_rank in users.json
        users[user_id]['path_review']['current_rank'] = rank
        
        # Add to ranking list in rank.json format
        ranking_list.append({
            'user_name': user_name,
            'like_count': like_count,
            'current_rank': rank
        })
    
    # Save updated users.json
    try:
        with open(users_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except IOError as e:
        raise IOError(f"Error writing to users.json: {e}")
    
    # Save ranking list to rank.json
    try:
        with open(rank_path, 'w', encoding='utf-8') as f:
            json.dump(ranking_list, f, ensure_ascii=False, indent=4)
    except IOError as e:
        raise IOError(f"Error writing to rank.json: {e}")
    
    return ranking_list


# if __name__ == "__main__":
#     # Example usage
#     try:
#         ranking_list = generate_comment_rank_list()
#         print("Comment ranking generated successfully!")
#         print(json.dumps(ranking_list, ensure_ascii=False, indent=2))
#     except Exception as e:
#         print(f"Error: {e}")