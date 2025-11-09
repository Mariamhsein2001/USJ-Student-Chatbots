import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from pydantic import BaseModel
from typing_extensions import TypedDict
from typing import List, Dict, Optional, Tuple,Union
from langchain_core.tools import tool
from tools.generate_timetable import generate_timetable

from utils.overlapping_times_checker import check_schedule_conflicts
from tools.course_advisor import combine_course_plans
from tools.user_course_info import get_course_context,get_user_context_dict
from tools.credits_courses import calculate_total_credits


class EligibilityInput(TypedDict):
    courses_by_semester: Dict[str, List[Dict[str, str]]]
    taken_codes: List[str]
    target_semester: str
    
class TimeSlot(BaseModel):
    start_time: str
    end_time: str
    session_type: Optional[str] = None
    weeks: str

class Course(BaseModel):
    course: str
    instructor: Optional[str] = None
    schedule: Dict[str, List[TimeSlot]]
    
class CourseWithGroup(BaseModel):
    course: str
    group: Optional[str] = None
    schedule: Dict[str, List[TimeSlot]]
    
@tool
def detect_schedule_conflicts(username: str, courses: List[Dict]) -> List[Tuple[str, str, str, str, str, List[int]]]:
    """
    Detect schedule conflicts for a given user, considering course groups.
    Each course dict should include:
        - 'course': str (the course name)
        - 'group': str or None  (optional)
        - 'schedule': dict[str, list[TimeSlot]]
    
    Args:
        username (str): The student's username to fetch full course schedules.
        courses (List[Dict]): List of courses to check for conflicts.

    Returns:
        list[tuple]: (course1, course2, day, time1, time2, overlapping_weeks)
    """
    # Get full course schedules for the user
    schedules = get_user_context_dict(username)['course_schedules']
    
    # Build a mapping (course + group) -> schedule
    schedule_map = {(s.get("course"), s.get("group")): s.get("schedule", {}) for s in schedules}

    # Prepare courses with schedules, using fallback if not provided
    courses_to_check = []
    for c in courses:
        course = c.get("course")
        group = c.get("group") or 'group_1'
        
        # Use provided schedule if exists; otherwise fallback to master schedule
        schedule = schedule_map.get((course, group), {})
        
        # Use course + group as identifier if group exists
        identifier = f"{course} - {group}" if group else course
        
        courses_to_check.append({
            "course": identifier,
            "schedule": schedule
        })

    # Call existing conflict checker
    return check_schedule_conflicts(courses_to_check)

@tool
def build_timetable(courses: List[Union[CourseWithGroup, Course, dict]]) -> str:
    """
    Generate a visual timetable as an HTML table from a list of courses.

    This tool can handle input in multiple formats:
    - Pydantic objects (`CourseWithGroup` or `Course`)
    - Plain dictionaries
    - Schedules nested by group or already flat

    Each course must include:
        - `course` (str): Name of the course.
        - `group` (optional, str): Group identifier.
        - `schedule` (dict): Dictionary of days mapping to a list of sessions.
          Each session must contain:
            - `start_time` (str, "HH:MM")
            - `end_time` (str, "HH:MM")
            - `session_type` (optional, str)
            - `weeks` (str, e.g., "all", "impaires", "paires")

    The function:
    1. Validates and normalizes input, converting schedules to `TimeSlot` objects.
    2. Flattens nested group schedules if present.
    3. Maps sessions to predefined 1h15 time blocks.
    4. Generates an HTML table representing the timetable.

    Returns:
        str: An HTML string representing the timetable. Empty slots are left blank,
             multiple sessions in the same block are stacked with `<hr>` separators.

    Raises:
        ValueError: If the course or session data is invalid or cannot be parsed.
    """
    validated_courses = []

    for c in courses:
        # If already a Pydantic object, keep it
        if isinstance(c, (Course, CourseWithGroup)):
            validated_courses.append(c)
            continue

        if not isinstance(c, dict):
            raise ValueError(f"Invalid course entry: {c}")

        # Extract schedule
        sched = c.get("schedule", {})

        # Flatten nested group schedules
        flat_schedule = {}
        for key, val in sched.items():
            if isinstance(val, dict):
                for day, slots in val.items():
                    flat_schedule.setdefault(day, []).extend(slots)
            else:
                flat_schedule.setdefault(key, []).extend(val)

        ts_schedule = {}
        for day, slots in flat_schedule.items():
            ts_schedule[day] = []
            for slot in slots:
                if isinstance(slot, dict):
                    ts_schedule[day].append(TimeSlot(**slot))
                elif isinstance(slot, TimeSlot):
                    ts_schedule[day].append(slot)
                else:
                    raise ValueError(f"Invalid session in course {c.get('course')} for {day}: {slot}")

        # Decide which class to use
        if "group" in c:
            course_obj = CourseWithGroup(
                course=c.get("course"),
                group=c.get("group"),
                schedule=ts_schedule
            )
        else:
            course_obj = Course(
                course=c.get("course"),
                schedule=ts_schedule
            )

        validated_courses.append(course_obj)

    # Convert to dicts for generate_timetable
    courses_dicts = [course.model_dump() for course in validated_courses]

    return generate_timetable(courses_dicts)

@tool
def course_distribution_advisor(username: str, interests: str) -> dict:
    """
    LangChain tool: Generates a balanced course distribution plan for a student.

    This tool:
    1. Uses LLM to suggest courses based on eligibility, GPA, and interests.
    2. Builds a non-conflicting schedule.
    
    Args:
        username (str): The student's username.
        interests (str): User's interests based on conversation.

    Returns:
        dict: {
            "advise": str,
            "final_schedule": dict
        }
    """
    result = combine_course_plans(username, interests)
    if "error" in result:
        return {"error": result["error"]}
    
    combined_raw = result.get("combined_raw", "")

    # Extract only the 'advise' field from the JSON inside combined_raw
    try:
        import json
        raw_str = combined_raw
        # remove markdown code block if present
        if raw_str.startswith("```json"):
            raw_str = raw_str.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw_str)
        advice_text = data.get("advise", "")
    except Exception:
        advice_text = combined_raw  # fallback to full raw content

    return {
        "advise": advice_text,
        "final_schedule": result.get("schedules", {})
    }

@tool
def course_context_lookup(username: str, intent: str ) -> Union[dict, list]:
    """
    Retrieve specific or complete academic and course-related context for a given student.

    This tool allows the LLM to fetch either the entire academic context or a 
    specific subset of data depending on the provided intent.

    Args:
        username (str): The student's unique username.
        intent (str, optional): The specific type of information to retrieve.
            Supported values include:
                - "user_info": General academic information (GPA, semester, etc.)
                - "eligibility": Eligible and not eligible courses
                - "availability": Current and previous semester available courses(all course infromation including description,instructors,)
                - "past_courses": Courses already completed
                - "course_schedules": All course schedules
                - "all_courses" : Course plan for the program of the student includes all courses for all semesters.

            Defaults to "user_info".

    Returns:
        dict or list
    """
    try:
        result = get_course_context(username=username, intent=intent)
        return result["courses"]
    except Exception as e:
        return {"error": f"Error retrieving context for '{username}' with intent '{intent}': {str(e)}"}

@tool
def calculate_total_credits_tool(username: str, course_names: List[str]) -> dict:
    """
    Tool wrapper around calculate_total_credits function.
    Calculates total credits for a list of course names for a given user.
    Input: 
        - course_names: list of course names only no codes included.
    """
    return calculate_total_credits(username, course_names)