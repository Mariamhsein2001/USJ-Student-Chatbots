# utils/db/db_utils.py

import sqlite3
from collections import defaultdict
from utils.db.queries import *


DB_PATH = "storage/data_store/advising.db"

def normalize_course_type(raw_type, user_track=None):
    """
    Normalize course types, handling track-specific overrides.
    """
    base_map = {
        "UE Obligatoires": "UE Obligatoires",
        "UE Obligatoires pour l’option-Génie Logiciel": "UE Obligatoires pour l’option",
        "UE Obligatoires pour l’option-Réseaux de Télécommunications": "UE Obligatoires pour l’option",
        "Optionnelles Fermées": "Optionnelles Fermées",
        "Optionnels Ouverts": "Optionnels Ouverts",
    }

    # Conditional track adjustments
    if user_track == "Génie Logiciel" and raw_type == "UE Obligatoires pour l’option-Réseaux de Télécommunications":
        return "Optionnelles Fermées"
    if user_track == "Réseaux de Télécommunications" and raw_type == "UE Obligatoires pour l’option-Génie Logiciel":
        return "Optionnelles Fermées"

    return base_map.get(raw_type, raw_type)

def run_query(query, params=(), fetchone=False, many=False):
    """Run a SQL query and return results (fetchone or fetchall)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall() if not fetchone else cursor.fetchone()
    conn.close()
    return result


def get_user_info(username: str):
    """Fetch basic info (id, semester, GPA, program, track) for a user."""
    row = run_query(GET_USER_INFO, (username,), fetchone=True)
    if not row:
        return None
    return {
        "user_id": row[0],
        "username": row[1],
        "current_semester": row[2],
        "gpa": row[3],
        "department": row[4],
        "program": row[5],
        "track": row[6],
    }


def get_courses_taken_by_user(user_id: int):
    """Fetch all courses taken by a user given their user_id."""
    rows = run_query(GET_USER_INFO_ROWS, (user_id,))
    if not rows:
        return []

    user_info_ids = [row[0] for row in rows]
    placeholders = ",".join("?" for _ in user_info_ids)
    query = GET_USER_COURSES.format(placeholders=placeholders)
    result = run_query(query, user_info_ids)

    return [{"code": row[0]} for row in result]


def get_courses_by_program_and_semester(program_name: str, semester: int):
    """Fetch courses for a program in a given semester (with schedule & instructor)."""
    rows = run_query(GET_COURSES_BY_PROGRAM_SEMESTER, (f"%{program_name}%", semester))

    grouped = defaultdict(lambda: {
        "schedule": defaultdict(list),
        "instructor": set(),
        "type": None,
        "extra_info": None,
        "code": None,
        "credits": None,
        "prerequisites": None
    })

    for row in rows:
        (provided_id, raw_name, group_name, course_type, extra_info,
         course_id, title, credits, prereqs,
         instructor, start, end, day, weeks, session_type) = row

        key = (raw_name, group_name)
        if instructor:
            grouped[key]["instructor"].add(instructor)
        if start and end and day:
            slot = {
                "start_time": start,
                "end_time": end,
                "weeks": weeks,
                "session_type": session_type
            }
            if slot not in grouped[key]["schedule"][day]:
                grouped[key]["schedule"][day].append(slot)

        grouped[key]["type"] = course_type
        grouped[key]["extra_info"] = extra_info
        grouped[key]["code"] = course_id
        grouped[key]["credits"] = credits
        grouped[key]["prerequisites"] = prereqs
        grouped[key]["title"] = title or raw_name
        grouped[key]["group_name"] = group_name

    return [
        {
            "course": info["title"],
            "code": info.get("code"),
            "credits": info.get("credits"),
            "prerequisites": info.get("prerequisites"),
            "instructor": ", ".join(sorted(info["instructor"])) if info["instructor"] else "Unknown",
            "group": group_name,
            "type": info.get("type"),
            "extra_info": info.get("extra_info"),
            "schedule": dict(info["schedule"])
        }
        for (raw_name, group_name), info in grouped.items()
    ]


def get_course_description_by_code(code: str):
    """Fetch course description using course code."""
    row = run_query(GET_COURSE_DESCRIPTION, (code,), fetchone=True)
    return row[0] if row else "No description available"


def check_user_credentials(username: str, password: str) -> bool:
    """Check if provided username and password match."""
    row = run_query(CHECK_USER_CREDENTIALS, (username,), fetchone=True)
    if row and row[0] == password:
        return True
    return False


def get_courses_with_status(username: str):
    """Fetch user’s courses with grades, status, and pass/fail flag."""
    rows = run_query(GET_COURSES_WITH_STATUS, (username,))
    return [
        {"code": r[0], "title": r[1], "grade": r[2], "status": r[3], "failed": bool(r[4])}
        for r in rows
    ]
    
    
def get_required_credits_by_type(username: str) -> dict:
    """
    Return expected total credits per course type for the user's current program.
    """
    user_info = get_user_info(username)
    if not user_info:
        return {}
    rows = run_query(GET_CREDIT_EXPECTED, (username,))
    return {ctype: total or 0 for ctype, total in rows}

def get_total_credits_by_type(username: str) -> dict:
    """
    Return a dict {course_type: total_credits} for the user's taken courses (grade >= 10).
    Normalizes track-specific course types.
    """
    # Get user track
    
    user_info = get_user_info(username)
    if user_info: 
        user_track = user_info["track"]

    # Fetch summed credits by course type
    rows = run_query(GET_USER_TOTAL_CREDITS_BY_TYPE_WITH_TRACK, (username,))

    credits_by_type = defaultdict(int)
    for raw_type, total in rows:
        norm_type = normalize_course_type(raw_type, user_track)
        credits_by_type[norm_type] += total or 0

    return dict(credits_by_type)

def get_academic_plan_courses(username: str):
    """
    Fetch academic plan courses for a user's program, including course_type from courses table.

    Returns a list of courses with code, title, credits, semester, and course_type.
    """

    user_info = get_user_info(username)
    if not user_info:
        print(f"[WARN] No user found with username: {username}")
        return []

    program_name = user_info["program"]

    # Fetch academic plan ID for this program and user's enrollment year
    query_plan = """
        SELECT ap.id
        FROM academic_plans ap
        JOIN programs p ON ap.program_id = p.id
        WHERE p.name LIKE ? 
        ORDER BY ap.academic_year DESC
        LIMIT 1
    """
    plan_row = run_query(query_plan, (f"%{program_name}%",), fetchone=True)
    if not plan_row:
        print(f"[WARN] No academic plan found for program '{program_name}'")
        return []

    plan_id = plan_row[0]

    # Fetch plan courses joined with courses table to get course_type
    query_courses = """
        SELECT apc.course_code, apc.course_title, apc.credits, apc.semester, c.course_type
        FROM academic_plan_courses apc
        LEFT JOIN courses c ON apc.course_code = c.course_id
        WHERE apc.plan_id = ?
        ORDER BY apc.semester, apc.course_title
    """
    rows = run_query(query_courses, (plan_id,))

    return [
        {
            "code": row[0],
            "title": row[1],
            "credits": row[2],
            "semester": row[3],
            "course_type": row[4]  
        }
        for row in rows
    ]

    
def main():
    username = "Karim"
    password = "testpassword"  # replace with actual password

    # Test user info
    user_info = get_user_info(username)
    print("User Info:", user_info)

    if user_info:
        user_id = user_info["user_id"]

        # Test courses taken
        courses_taken = get_courses_taken_by_user(user_id)
        print(f"\nCourses taken by {username}:")
        for c in courses_taken:
            print(c)

        # Test courses by program and semester
        current_semester = user_info["current_semester"]
        courses_offered = get_courses_by_program_and_semester(user_info["program"], current_semester)
        print(f"\nCourses offered for {user_info['program']} semester {current_semester}:")
        for c in courses_offered[:5]:  # show first 5 for brevity
            print(c)

        # Test course description by code
        if courses_taken:
            code = courses_taken[0]["code"]
            description = get_course_description_by_code(code)
            print(f"\nDescription for {code}:", description)

    # Test credentials
    valid = check_user_credentials(username, password)
    print(f"\nCredentials valid for {username}:", valid)

    # Test courses with status
    courses_status = get_courses_with_status(username)
    print(f"\nCourses with status for {username}:")
    for c in courses_status:
        print(c)
        
    credit_type = get_total_credits_by_type('Karim')
    print(credit_type)


if __name__ == "__main__":
    main()