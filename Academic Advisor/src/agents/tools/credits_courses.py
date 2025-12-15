
import logging
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from agents.tools.user_course_info import get_user_context_dict

def calculate_total_credits(username, course_names):
    """
    Given a list of course names, calculates the total credits
    using the user's eligible_courses from their context, and
    returns the credits for each course as well.

    Args:
        username (str): The student's username.
        course_names (List[str]): List of course names to sum credits for.

    Returns:
        dict: {
            "total_credits": int,
            "course_credits": Dict[str, int]  # course_name -> credits
        }
    """
    # Fetch user context (from cache if possible)
    context = get_user_context_dict(username)
    if "error" in context:
        raise ValueError(f"Cannot fetch user context: {context['error']}")

    eligible_courses = context.get("eligibility", [])['eligible_courses']

    # Build a mapping of course title -> credits
    course_credits_map = {course["title"]: course.get("credits", 0) for course in eligible_courses}

    total_credits = 0
    selected_course_credits = {}

    for cname in course_names:
        credits = course_credits_map.get(cname)
        if credits is None:
            print(f"Course '{cname}' not found in eligible courses, skipping.")
            continue
        selected_course_credits[cname] = credits
        total_credits += credits
    return {
        "total_credits": total_credits,
        "course_credits": selected_course_credits
    }
def credit_analysis(username, simple_courses, gpa):
    """
    Enforce credit limits based on GPA.
    If exceeded, remove courses by priority and
    return ONLY the remaining courses.
    """

    # Calculate total credits
    course_names = [c['course'] for c in simple_courses]
    credits_data = calculate_total_credits(username, course_names)

    total_credits = credits_data['total_credits']
    course_credits = credits_data['course_credits']  # dict: {course_name: credits}

    print(f"Total calculated credits for user '{username}': {total_credits}")

    # Credit limit
    credit_limit = 30 if gpa < 12 else 36

    remaining_courses = simple_courses.copy()

    if total_credits <= credit_limit:
        return remaining_courses

    excess = total_credits - credit_limit
    print(f"Total credits {total_credits} exceed limit {credit_limit} by {excess}. Adjusting...")

    # Group courses by type
    courses_by_type = {}
    for c in remaining_courses:
        ctype = c.get("type", "Other")
        courses_by_type.setdefault(ctype, []).append(c)

    # Removal priority (FIXED)
    drop_priority = [
        "Optionnelle Ouverte",
        "Optionnelle Fermée",
        "UE Obligatoires pour l’option",
        "UE Obligatoires",
        "Required Previous"
    ]

    # Remove courses until within limit
    for ctype in drop_priority:
        if excess <= 0:
            break

        candidates = []

        for course in courses_by_type.get(ctype, []):
            course_name = course["course"]
            course_credit = course_credits.get(course_name, 0)

            if course_credit > 0:
                candidates.append((course, course_credit))

        if not candidates:
            continue

        # Select course with credits closest to excess
        course_to_remove, credit_value = min(
            candidates,
            key=lambda x: abs(x[1] - excess)
        )

        logging.info(
            f"Removing course '{course_to_remove['course']}' "
            f"of type '{ctype}' with {credit_value} credits "
            f"(closest match to excess {excess})."
        )

        remaining_courses.remove(course_to_remove)
        excess -= credit_value

        if excess <= 0:
            break

    return remaining_courses