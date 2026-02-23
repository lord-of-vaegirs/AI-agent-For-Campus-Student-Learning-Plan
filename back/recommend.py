import json
import os
import sys
import streamlit as st

# DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except (FileNotFoundError, KeyError, AttributeError):
    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

_SESSION_CACHE = {}

def stream_conversation_for_plan(user_id, demand):
    """
    Function to handle streaming conversation for generating a personalized learning plan.

    Args:
        user_id (str): The ID of the user to fetch data for.
        demand (str): The user's specific demand or request.

    Returns:
        generator: A generator that yields the response from the LLM in a streaming manner.
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

    # Step 1: Load user data from users.json
    users = load_json('../databases/users.json', 'users.json')

    # Step 2: Find the user by user_id
    if isinstance(users, dict):
        user_info = users.get(user_id)
    else:
        user_info = next((user for user in users if user.get("id") == user_id), None)

    if not user_info:
        raise ValueError(f"User with ID {user_id} not found in users.json.")

    profile = user_info.get("profile", {})
    major = profile.get("major")
    current_semester = user_info.get("academic_progress", {}).get("current_semester")
    if not major:
        raise ValueError(f"User with ID {user_id} does not have a major in users.json.")

    # Step 3: Load the prompt template from recommend_en.txt
    prompt_path = os.path.join(base_dir, '../prompts/recommend_en.txt')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        raise FileNotFoundError("recommend_en.txt file not found.")

    # Step 4: Load and filter databases by major
    contests = load_json('../databases/contests.json', 'contests.json')
    courses = load_json('../databases/courses.json', 'courses.json')
    research = load_json('../databases/research.json', 'research.json')
    course_requirement = load_json('../databases/course_requirement.json', 'course_requirement.json')

    def filter_by_major(data, restrict_courses=False):
        result = []
        for school in data.get("学院列表", []):
            for major_info in school.get("专业列表", []):
                if major_info.get("专业名称") == major:
                    if restrict_courses and current_semester is not None:
                        filtered_major = dict(major_info)
                        filtered_courses = []
                        for course in major_info.get("课程列表", []):
                            offered_semester = course.get("standard_semester")
                            if offered_semester == current_semester:
                                filtered_courses.append(course)
                        filtered_major["课程列表"] = filtered_courses
                        major_info = filtered_major
                    result.append({
                        "学院名称": school.get("学院名称"),
                        "专业": major_info
                    })
        return result

    contests_by_major = filter_by_major(contests)
    courses_by_major = filter_by_major(courses, restrict_courses=True)
    research_by_major = filter_by_major(research)
    course_requirement_by_major = filter_by_major(course_requirement)

    # Step 5: Build a stable base prompt (first-turn context)
    base_prompt = (
        f"{prompt_template}\n\n"
        f"User Profile: {json.dumps(user_info, ensure_ascii=False)}\n\n"
        f"Major-Scoped Databases:\n"
        f"contests.json: {json.dumps(contests_by_major, ensure_ascii=False)}\n"
        f"courses.json: {json.dumps(courses_by_major, ensure_ascii=False)}\n"
        f"research.json: {json.dumps(research_by_major, ensure_ascii=False)}\n"
        f"course_requirement.json: {json.dumps(course_requirement_by_major, ensure_ascii=False)}"
    )

    # Step 6: Maintain multi-turn context in memory (per user_id)
    session = _SESSION_CACHE.get(user_id)
    if not session:
        session = {
            "base_prompt": base_prompt,
            "turns": [],
            "assistant_responses": []
        }
        _SESSION_CACHE[user_id] = session

    session["turns"].append({"role": "user", "content": demand})

    recent_assistant_responses = session["assistant_responses"][-2:]
    recent_assistant_text = "\n".join(
        f"Assistant: {text}" for text in recent_assistant_responses
    )

    turns_text = f"User: {demand}"

    first_prompt = (
        f"{session['base_prompt']}\n\n"
        f"Recent Assistant Replies:\n{recent_assistant_text}\n\n"
        f"Conversation History:\n{turns_text}\n\n"
        "Assistant:"
    )

    # Step 7: Interact with the cloud LLM (DeepSeek streaming)
    def llm_stream_response(prompt):
        """
        Stream response from DeepSeek's OpenAI-compatible API.
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
            "stream": True,
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
                for raw_line in resp:
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Failed to connect to DeepSeek at {base_url}.") from exc

    # Step 8: Return the streaming response from the LLM and store it
    def stream_and_store():
        # First request: generate an initial response.
        first_chunks = []
        for chunk in llm_stream_response(first_prompt):
            first_chunks.append(chunk)
        first_response = "".join(first_chunks).strip()

        # Second request: validate and correct the first response.
        second_prompt = (
            f"{session['base_prompt']}\n\n"
            f"User Demand:\n{demand}\n\n"
            f"Draft Response:\n{first_response}\n\n"
            "Validation Request: 请验证第一轮的draft response是否符合回复要求，是否合理准确。\n"
            "Do not mention any secondary verification in your reply (e.g., \"经过二次验证\").\n\n"
            "Assistant:"
        )

        second_chunks = []
        for chunk in llm_stream_response(second_prompt):
            second_chunks.append(chunk)
            yield chunk

        final_response = "".join(second_chunks).strip()
        if final_response:
            session["assistant_responses"].append(final_response)

    return stream_and_store()


if __name__ == "__main__":
    # Example usage
    user_id = "user_2023000001"
    demands = [
        "请为我规划一下本学期应该选择什么个性化选修课",
        "请为我规划一下本学期应该选择什么适合我的科研",
        "请为我规划一下本学期应该选择什么适合我的竞赛",
        "请为我规划一下本学期的选择"
    ]

    # Create output directory if not exists
    output_dir = os.path.join(os.path.dirname(__file__), '../test_output')
    os.makedirs(output_dir, exist_ok=True)

    # Create output file with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f'recommendation_test_{timestamp}.txt')

    print(f"Starting test... Output will be saved to: {output_file}")
    print("Generating recommendations...\n")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"User ID: {user_id}\n")
        f.write("="*80 + "\n\n")

        for idx, demand in enumerate(demands, start=1):
            f.write(f"Round {idx} Demand: {demand}\n")
            f.write("-"*80 + "\n")
            f.write("LLM Response:\n\n")
            print(f"\n--- Round {idx} ---\n")

            for response in stream_conversation_for_plan(user_id, demand):
                print(response, end='', flush=True)
                f.write(response)

            f.write("\n\n")

    print(f"\n\nTest completed! Results saved to: {output_file}")