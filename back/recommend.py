import json
import os
import sys

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

    def filter_by_major(data):
        result = []
        for school in data.get("学院列表", []):
            for major_info in school.get("专业列表", []):
                if major_info.get("专业名称") == major:
                    result.append({
                        "学院名称": school.get("学院名称"),
                        "专业": major_info
                    })
        return result

    contests_by_major = filter_by_major(contests)
    courses_by_major = filter_by_major(courses)
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
            "turns": []
        }
        _SESSION_CACHE[user_id] = session

    session["turns"].append({"role": "user", "content": demand})

    turns_text = "\n".join(
        f"User: {turn['content']}" for turn in session["turns"]
    )

    prompt = (
        f"{session['base_prompt']}\n\n"
        f"Conversation History:\n{turns_text}\n\n"
        "Assistant:"
    )

    # Step 7: Interact with the local LLM (Ollama streaming)
    def llm_stream_response(prompt):
        """
        Stream response from a local Ollama model.
        Set OLLAMA_HOST or OLLAMA_MODEL env vars to override defaults.
        """
        import urllib.request

        base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        model_name = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

        payload = json.dumps({
            "model": model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_ctx": 32768
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for raw_line in resp:
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("done"):
                        break
                    if "response" in data:
                        yield data["response"]
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Failed to connect to Ollama at {base_url}.") from exc

    # Step 8: Return the streaming response from the LLM
    return llm_stream_response(prompt)


if __name__ == "__main__":
    # Example usage
    user_id = "user_2023000001"
    demand = "Based on my profile and the available courses, research projects, and competitions, please provide direct recommendations for: 1) personalized elective courses I should take next semester, 2) research projects that align with my goals, and 3) competitions I should participate in. After your recommendations, ask if I need any clarifications or have other requirements."
    
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
        f.write(f"Demand: {demand}\n")
        f.write("="*80 + "\n\n")
        f.write("LLM Response:\n\n")
        
        for response in stream_conversation_for_plan(user_id, demand):
            print(response, end='', flush=True)
            f.write(response)
    
    print(f"\n\nTest completed! Results saved to: {output_file}")