import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from concurrent.futures import ThreadPoolExecutor
from core.llm import get_llm
from pydantic import BaseModel
from typing import List, Literal
from utils.utilities import clean_gemini_json, format_schedule_for_llm
from utils.conflicting_groups import finalize_non_conflicting_schedule
from src.agents.tools.credit_agent import generate_credits_interests_plan
from src.agents.tools.course_selection_agent import generate_course_selection_plan
from core.context import fetch_user_context
import time
from core.cache import GLOBAL_CACHE_STORE 
from src.agents.tools.credits_courses import credit_analysis

# Pydantic models
class CourseItem(BaseModel):
    code: str
    course: str
    credits: int
    course_type: Literal[
        "Required Previous",
        "UE Obligatoires",
        "UE Obligatoires pour l’option",
        "Optionnelle Fermée",
        "Optionnelle Ouverte"
    ]
    reason: str = ""

class CoursePlan(BaseModel):
    recommended_courses: List[CourseItem]
    advise: str = ""

# Single shared LLM for all calls
llm = get_llm()

def combine_course_plans(username: str, interests: str = "") -> dict:
    """Generate final course plan by combining credits/interests and past performance plans with timing logs."""

    timings = {}
    start_total = time.time()
    
    # --- CACHE-FIRST CONTEXT RETRIEVAL using GLOBAL_CACHE_STORE ---
    t_cache_start = time.time()
    cached_data = GLOBAL_CACHE_STORE.get(("user_context",), username)
    
    if cached_data:
        context = cached_data.value
        print(f"Context loaded from cache for user: {username}")
    else:
        context = fetch_user_context(username)
        GLOBAL_CACHE_STORE.put(("user_context",), username, context)
        print(f"Context fetched from source and cached for user: {username}")
        
    timings["context_retrieval"] = time.time() - t_cache_start
    # --- END CACHE LOGIC ---
    
    # --- STREAMLINED PARALLEL LLM EXECUTION ---
    t1 = time.time()
    
    # Create the single input dictionary required by the planners
    # This avoids multiple dictionary copies
    planner_input = context.copy()
    username= planner_input['username'] 
    gpa = planner_input['gpa'] 
    semester = planner_input['semester']
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Pass the single input dictionary to the functions
        future_credits = executor.submit(generate_credits_interests_plan, planner_input, llm, interests)
        future_past = executor.submit(generate_course_selection_plan, planner_input, llm,interests)

        plan_credits = future_credits.result()
        plan_past = future_past.result()

    timings["parallel_llms"] = time.time() - t1
    # print(plan_credits['recommendation'])
    # Build merge prompt
    merge_prompt = f"""
You are a senior academic advisor assistant.

Below are two suggested course plans generated separately:
1. Credits focused plan (consider the total number of credits from here to build the final plan):
{plan_credits['recommendation']}

2. Past Performance and Interests focused plan (consider to select the courses from here based on the student's past performance and interests):
{plan_past['recommendation']}

User Interests: 
{interests}

Please merge these recommendations into a single cohesive course plan for the student with gpa {gpa},
avoiding duplication, using recommended number of credits,prioritizing required and core courses, and providing a clear total credit summary.

Rules:
- Each course must include: code, name, credits, course_type, and reason.
- MAKE SURE TO CONSIDER  the total credits from Credits focused plan and user interests return the total credits.
- The total number of credits should be minimum 28 and maximum 36 unless requested otherwise from Credits & Interests plan or user.
- If gpa is less than 12 , maximum number of credits is 30 credits regardless of user's number of credits.
- Include general advise for the student.
- Give reasoning for each course selection.
- Max 2 Optionnelle Fermée courses should be selected.
- Ensure the **total credits match the student’s target** if possible.
- DONOT return fake course codes or names.
- If {semester} semester, then 1 Optionnelle Fermée courses should be selected.
- MAKE sure the advise is well thought off and is in the best interests for the student and what benefits them.
- Return ONLY valid JSON matching this schema:

{CoursePlan.model_json_schema()}
"""

    # Gemini call to merge plans (The unavoidable bottleneck)
    t2 = time.time()
    try:
        response = llm.generate_content(merge_prompt)
        combined_raw = response.text.strip() if hasattr(response, "text") else str(response)
    except Exception as e:
        combined_raw = f"Gemini error: {str(e)}"
    timings["merge_llm"] = time.time() - t2


    # Clean JSON and validate
    t3 = time.time()
    cleaned = clean_gemini_json(combined_raw)
    try:
        final_plan = CoursePlan.model_validate_json(cleaned)
    except Exception as e:
        final_plan = CoursePlan(
            recommended_courses=[],
            advise=f"Parsing failed: {e}\nRaw: {combined_raw}"
        )
    timings["json_parsing"] = time.time() - t3

    # Simplify course info
    simple_courses = [
        {"code": c.code, "course": c.course, "type": c.course_type}
        for c in final_plan.recommended_courses
    ]
    if semester > 1:
        print("Performing credit analysis based on GPA...")
        simple_courses = credit_analysis(username, simple_courses, gpa)


    # Generate non-conflicting schedules
    t4 = time.time()
    schedules = finalize_non_conflicting_schedule(username, simple_courses)
    timings["schedule_building"] = time.time() - t4

    structured_schedules = format_schedule_for_llm(schedules)
    timings["total_runtime"] = time.time() - start_total
    print("=== TIMINGS ===")
    for k, v in timings.items():
        print(f"{k}: {v:.2f} sec")
    # print(schedules)
    return {
        "plan_credits": plan_credits,
        # "plan_past": plan_past,
        # "merge_prompt": merge_prompt,
        "combined_raw": combined_raw,
        # "final_plan": final_plan.model_dump(),
        # "courses": simple_courses,
        "schedules": schedules,
        "schedule_formatted": structured_schedules
    }


if __name__ == "__main__":
    result = combine_course_plans("Alice",interests="AI and data science interests, prefers 36 credits, wants balanced workload")
    print(result["plan_credits"])
    print(result["combined_raw"])
    for sched_name, sched in result["schedules"].items():
        print("--------", sched_name, "--------")
        for c in sched:
            print(c['course'], c['group'])
