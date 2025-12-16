
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
    Analyze student's total credits and GPA to check compliance with credit limits
    and suggest drops if the limit is exceeded.
    """
    # Get course names and total credits
    course_names = [c['course'] for c in simple_courses]
    total_credits = calculate_total_credits(username, course_names)['total_credits']

    # Determine credit limit based on GPA (probation rule)
    if gpa < 12:
        credit_limit = 30
    else:
        credit_limit = 36

    message = ""
    suggestions = []

    # Compare total credits with allowed limit
    if total_credits > credit_limit:
        excess = total_credits - credit_limit
        message += f"You exceeded the credit limit by {excess} credits.\n\n"

        # Group courses by type
        courses_by_type = {}
        for c in simple_courses:
            ctype = c.get("type", "Other")
            courses_by_type.setdefault(ctype, []).append(c)

        # Prioritize removable types
        drop_priority = ["Optionnelle Ouverte", "Optionnelle Fermée", "UE Obligatoires","Required Previous"]

        # Suggest drops
        for ctype in drop_priority:
            for course in courses_by_type.get(ctype, []):
                suggestions.append((course["course"], course["code"], course.get("credits", 0)))
                excess -= course.get("credits", 0)
                if excess <= 0:
                    break
            if excess <= 0:
                break

        if suggestions:
            message += "Suggested courses to drop:\n" + "\n".join(
                f"- {name} ({code})" for name, code, _ in suggestions
            )
        else:
            message += "No suitable courses found to drop based on course type."

    else:
        remaining = credit_limit - total_credits
        message = (
            f"You are within the credit limit ({total_credits}/{credit_limit} credits).\n"
            f"You can still take up to {remaining} more credits if desired."
        )

    # Return structured result
    return {
        "total_credits": total_credits,
        "suggestions": suggestions,
        "message": message.strip(),
    }
