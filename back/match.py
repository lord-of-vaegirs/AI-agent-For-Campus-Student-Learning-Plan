import json
import os
import re
import streamlit as st

# DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"] if "DEEPSEEK_API_KEY" in st.secrets else os.environ.get("DEEPSEEK_API_KEY", "")

def stream_conversation_for_match(user_id):
    """
    Function to handle learning path matching for a user.

    Args:
        user_id (str): The ID of the user to perform matching for.

    Returns:
        list: A list of 3 most similar user IDs (format: "user_学工号").
    """
    base_dir = os.path.dirname(__file__)

    def load_json(relative_path, file_label):
        file_path = os.path.join(base_dir, relative_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"{file_label} file not found.")
        except json.JSONDecodeError:
            raise ValueError(f"Error decoding {file_label} file.")

    # Step 1: Load user database from users.json
    users = load_json('../databases/users.json', 'users.json')

    # Step 2: Find the target user by user_id
    if isinstance(users, dict):
        target_user_info = users.get(user_id)
    else:
        target_user_info = next((user for user in users if user.get("id") == user_id), None)

    if not target_user_info:
        raise ValueError(f"User with ID {user_id} not found in users.json.")

    # Step 3: Load the prompt template from match_en.txt
    prompt_path = os.path.join(base_dir, '../prompts/match_en.txt')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        raise FileNotFoundError("match_en.txt file not found.")

    # Step 4: Build the base prompt with target user and all users data
    base_prompt = (
        f"{prompt_template}\n\n"
        f"Target User Profile:\n{json.dumps(target_user_info, ensure_ascii=False)}\n\n"
        f"All Users Database:\n{json.dumps(users, ensure_ascii=False)}"
    )

    # Step 5: Define LLM response function
    def llm_response(prompt):
        """
        Get response from DeepSeek's OpenAI-compatible API.
        Set DEEPSEEK_API_KEY and optionally DEEPSEEK_MODEL/DEEPSEEK_BASE_URL.
        """
        import urllib.request

        api_key = os.environ.get("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY)
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")

        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model_name = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

        payload = json.dumps({
            "model": model_name,
            "stream": False,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                choices = response_data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Failed to connect to DeepSeek at {base_url}.") from exc

    # Step 6: First request - initial matching
    first_prompt = (
        f"{base_prompt}\n\n"
        "Please identify the 3 most similar users based on learning experiences.\n"
        "Assistant:"
    )

    first_response = llm_response(first_prompt)

    # Step 7: Second request - validate and refine the first response
    second_prompt = (
        f"{base_prompt}\n\n"
        f"Initial Matching Result:\n{first_response}\n\n"
        "Validation Request: 请验证上面的匹配结果是否正确合理。\n"
        "Do not mention any secondary verification in your reply (e.g., \"经过二次验证\").\n"
        "Please identify the 3 most similar users based on learning experiences.\n"
        "Assistant:"
    )

    final_response = llm_response(second_prompt)

    # Step 8: Extract user IDs from the final response
    # Look for pattern "user_xxxxxx" (user_ followed by digits)
    user_id_pattern = r'user_\d+'
    matched_ids = re.findall(user_id_pattern, final_response)
    
    # Return first 3 unique matched IDs (excluding the target user)
    unique_ids = []
    for uid in matched_ids:
        if uid not in unique_ids and uid != user_id:
            unique_ids.append(uid)
        if len(unique_ids) == 3:
            break

    return unique_ids


if __name__ == "__main__":
    # Example usage
    user_id = "user_2023000001"
    
    print(f"Finding similar users for: {user_id}\n")
    result = stream_conversation_for_match(user_id)
    
    print(f"Top 3 similar users:")
    for idx, uid in enumerate(result, 1):
        print(f"{idx}. {uid}")

