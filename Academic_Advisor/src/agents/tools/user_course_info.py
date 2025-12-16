import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from core.context import fetch_user_context
from core.cache import GLOBAL_CACHE_STORE
from utils.db.db_utils import get_courses_by_program_and_semester
from utils.course_eligibility import analyzing_eligibility
from utils.utilities import all_courses

def deduplicate_courses(course_list):
    seen = set()
    unique_courses = []
    for c in course_list:
        key = (c.get("code"), c.get("course"))
        if key not in seen:
            unique_courses.append(c)
            seen.add(key)
    return unique_courses

def get_user_context_dict(username: str) -> dict:
    """
    Returns a standardized dictionary for the user's academic context.
    Tries to load from GLOBAL_CACHE_STORE first. If not present, fetches and caches it.

    Example access: context["gpa"], context["eligible_courses"], etc.
    """
    try:
        #1. Load from cache or fetch fresh context
        cached_context_data = GLOBAL_CACHE_STORE.get(("user_context",), username)
        if cached_context_data:
            context = cached_context_data.value
            print(f"[CACHE HIT] Context retrieved for user: {username}")
        else:
            context = fetch_user_context(username)
            if not context or "error" in context:
                return {"error": f"No context found for user '{username}' or error: {context.get('error', None)}"}
            GLOBAL_CACHE_STORE.put(("user_context",), username, context)
            print(f"[CACHE MISS] Context fetched and stored for user: {username}")

        user = context.get("user", {})
        semester = context.get("semester")
        available_courses = get_courses_by_program_and_semester(user["program"], semester)
        data = analyzing_eligibility(username)

        # 2. Build a mapping of {code: description} from eligible_courses
        eligible = context.get("eligible_courses", [])
        code_to_description = {}
        for ec in eligible:
            code = ec.get("code")
            desc = ec.get("description")
            if code and desc:
                code_to_description[code] = desc

        # 3. Build previous semester courses (no schedule, but with description)
        previous_semester_courses = []
        schedules = []

        for sem, courses in data.get("courses_to_take_by_semester", {}).items():
            for course in courses:
                schedule = course.get("schedule")
                if schedule:
                    schedules.append({
                        "course": course.get("course"),
                        "code": course.get("code"),
                        "group": course.get("group"),
                        "semester": sem,
                        "schedule": schedule
                    })

                course_code = course.get("code")
                previous_semester_courses.append({
                    "semester": sem,
                    "course": course.get("course"),
                    "code": course_code,
                    
                    "credits": course.get("credits"),
                    "instructor": course.get("instructor"),
                    "group": course.get("group"),
                    "description": code_to_description.get(course_code)
                })

        # 4. Unmet courses
        unmet_courses = [
            {
                "course": c["course"],
                "code": c.get("code"),
                "explanation": c.get("explanation")
            }
            for c in data.get("unmet_not_found", [])
        ]

        # 5. Clean eligible courses (remove description + unnecessary fields)
        keys_to_remove = [
            "importance", "weight", "difficulty", "instructor", 
            "code",  "prereqs_met", "availability", "description"
        ]
        eligible_courses = [
            {k: v for k, v in course.items() if k not in keys_to_remove}
            for course in eligible
        ]

        # 6. Process current available courses (no schedule, add description)
        courses_no_schedule = []
        for c in available_courses:
            schedule = c.pop("schedule", None)
            code = c.get("code")
           

            # attach description by course code if available
            c["description"] = code_to_description.get(code)
            courses_no_schedule.append(c)

            if schedule:
                schedules.append({
                    "course": c.get("course"),
                    "code": code,
                    "group": c.get("group"),
                    "semester": semester,
                    "schedule": schedule
                })

        # 7. Merge additional schedules from data
        merged_schedules = data.get("course_schedules", []).copy()
        merged_schedules.extend(schedules)

        # 8. Remove duplicates (same course, group, semester)
        unique_schedules = []
        seen = set()
        for s in merged_schedules:
            key = (s.get("course"), s.get("group"), s.get("semester"))
            if key not in seen:
                unique_schedules.append(s)
                seen.add(key)
                
        courses_no_schedule = deduplicate_courses(courses_no_schedule)
        previous_semester_courses = deduplicate_courses(previous_semester_courses)

        # 9. Final standardized context
        return {
        "user_info": {
            "username": username,
            "gpa": context.get("gpa"),
            "semester": semester,
            "track": context.get("track") or None,
            "user": user,
            "credit_summary": context.get("credit_summary", {}),
            "semester_status": context.get("semester_status", {})
        },

        "eligibility": {
            "eligible_courses": eligible_courses,          # cleaned (no desc)
            "not_eligible_courses": unmet_courses,         # unmet prerequisites
        },
        "past_courses": context.get("past_courses", []),  # completed courses
        "availability": {
            "available_courses_current": courses_no_schedule,         # includes desc, no schedule
            "available_courses_previous": previous_semester_courses,  # includes desc, no schedule
                    },
        "course_schedules": unique_schedules ,
        "all_courses":all_courses(username)

    }


    except Exception as e:
        return {"error": f"Exception in get_user_context_dict: {e}"}



def get_course_context(username: str, intent: str) -> dict:
    """
    Fetch specific course-related data based on LLM-detected intent,
    aligned with the grouped structure of get_user_context_dict().

    Args:
        username (str): The student's username.
        intent (str): The intent detected by the LLM 
                      (e.g., 'user_info', 'eligibility', 'availability', 'past_courses', 'course_schedules').

    Returns:
        dict: {
            "intent": str,
            "courses": dict or list,
            "message": str
        }
    """

    context = get_user_context_dict(username)
    if "error" in context:
        return {"error": context["error"]}

    intent = intent.lower().strip()

    # Extract grouped data
    user_info = context.get("user_info", {})
    eligibility = context.get("eligibility", {})
    availability = context.get("availability", {})
    past_courses = context.get("past_courses", [])
    schedules = context.get("course_schedules", [])
    all_courses = context.get("all_courses", [])

    # Intent-based responses
    if intent == "user_info":
        return {
            "intent": intent,
            "courses": {
                "user_info": {
                    "username": user_info.get("username"),
                    "gpa": user_info.get("gpa"),
                    "semester": user_info.get("semester"),
                    "track": user_info.get("track"),
                    "user": user_info.get("user", {}),
                    "credit_summary": user_info.get("credit_summary", {}),
                    "semester_status": user_info.get("semester_status", {})
                }
            },
            "message": f"Academic information and current standing for {user_info.get('username', 'N/A')}."
        }

    elif intent == "eligibility":
        return {
            "intent": intent,
            "courses": {
                "eligible_courses": eligibility.get("eligible_courses", []),
                "not_eligible_courses": eligibility.get("not_eligible_courses", [])
            },
            "message": (
                f"Eligible and ineligible courses for Semester {user_info.get('semester', 'N/A')} "
                "based on prerequisite status."
            )
        }

    elif intent == "availability":
        return {
            "intent": intent,
            "courses": {
                "available_courses_current": availability.get("available_courses_current", []),
                "available_courses_previous": availability.get("available_courses_previous", [])
            },
            "message": (
                f"Courses available for the current semester (Semester {user_info.get('semester', 'N/A')}) "
                "and previous semesters."
            )
        }

    elif intent == "past_courses":
        return {
            "intent": intent,
            "courses": {"past_courses": past_courses},
            "message": "Courses you have already completed."
        }

    elif intent == "course_schedules":
        return {
            "intent": intent,
            "courses": {"course_schedules": schedules},
            "message": "Complete list of all course schedules."
        }
        
    elif intent == "all_courses":
        return {
            "intent": intent,
            "courses": {"all_courses": all_courses},
            "message": "ALL courses from all semesters for the program"
        }

    # Default
    return {
        "intent": "unknown",
        "courses": context,
        "message": f"No matching data found for intent '{intent}'."
    }

