# src/core/context.py
import os,sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.credit_checker import is_on_track, user_credits_summary
from utils.recommended_courses import recommend_courses_for_user
from utils.db.db_utils import get_user_info, get_courses_with_status
from utils.conflicting_groups import get_user_conflict_groups
from utils.utilities import format_courses_for_llm, summarize_past_courses,format_courses_for_credits


def fetch_user_context(username: str) -> dict:
    """
    Fetch all necessary student data once and return as context.
    Parallelize DB and computation tasks for speed.
    """
    user = get_user_info(username)
    if not user:
        return {"error": f"User '{username}' not found."}

    semester = user.get("current_semester", 1)

    # --- Define tasks for parallel execution ---
    tasks = {
        "credit_summary": lambda: user_credits_summary(username),
        "semester_status": lambda: is_on_track(username, semester),
        "eligible_courses": lambda: recommend_courses_for_user(username),
        "conflict_groups": lambda: get_user_conflict_groups(username),
        "past_courses": lambda: get_courses_with_status(username),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_key = {executor.submit(fn): key for key, fn in tasks.items()}

        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = f"Error fetching {key}: {e}"

    # Build context
    context = {
        "username": username,
        "user": user,
        "gpa": user.get("gpa"),
        "semester": semester,
        "track": user.get("track") if semester >= 3 else None,
        "credit_summary": results.get("credit_summary", {}),
        "semester_status": results.get("semester_status", {}),
        "eligible_courses": results.get("eligible_courses", []),
        "conflict_groups": results.get("conflict_groups", []),
        "past_courses": results.get("past_courses", []),
    }

    # Derived summaries (formatting)
    context["formatted_courses"] = format_courses_for_llm(context["eligible_courses"])
    context["formatted_courses_credits"] = format_courses_for_llm(context["eligible_courses"],False)
    context["past_summary"] = summarize_past_courses(context["past_courses"])
    print("data loaded")
    return context
