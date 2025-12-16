from collections import defaultdict

from utils.db.db_utils import get_total_credits_by_type,get_required_credits_by_type


def user_credits_summary(username: str) -> dict:
    """
    Compare user's taken credits vs expected program credits.
    Filters out None course types.
    """
    taken = get_total_credits_by_type(username)
    expected = get_required_credits_by_type(username)

    summary = {}
    all_types = set(taken.keys()).union(expected.keys())
    for ctype in all_types:
        if ctype is None:
            continue  # skip None types
        summary[ctype] = {
            "taken": taken.get(ctype, 0),
            "expected": expected.get(ctype, 0)
        }
    return summary

def credit_checker(courses, gpa=None, credit_limit=36):
    """
    Analyze total credits and suggest drops if above limit. Adjust credit limit based on GPA.
    """
    credit_limit = 30 if gpa is not None and gpa < 12 else credit_limit
    total_credits = 0
    credit_breakdown = defaultdict(int)
    courses_by_type = defaultdict(list)

    for course in courses:
        credits = course.get("credits") or 0
        ctype = course.get("type", "required")
        total_credits += credits
        credit_breakdown[ctype] += credits
        courses_by_type[ctype].append(course)

    message = f"Total planned credits: {total_credits} / {credit_limit}.\n"
    suggestions = []

    if total_credits > credit_limit:
        excess = total_credits - credit_limit
        message += f"Over limit by {excess} credits. Suggested drops:\n"
        for ctype in ["optional", "prerequisites"]:
            for course in courses_by_type.get(ctype, []):
                suggestions.append((course["course"], course["credits"]))
                excess -= course["credits"]
                if excess <= 0:
                    break
            if excess <= 0:
                break
        if suggestions:
            message += "\n".join(f"- {name} ({cr} cr)" for name, cr in suggestions)
        else:
            message += "No removable courses found based on type."
    else:
        message += "You're within the credit limit."

    return {
        "total_credits": total_credits,
        "credit_limit": credit_limit,
        "credit_breakdown": dict(credit_breakdown),
        "credit_message": message,
        "over_limit_suggestions": suggestions
    }


def is_on_track(username: str, semester: int) -> dict:
    """
    Check if the student's total credits are within the recommended range for the semester.
    """
    semester_ranges = {
        1: (30, 36),
        2: (60, 72),
        3: (90, 108),
        4: (120, 144),
        5: (150, 180),
        6: (180, 210)
    }
    taken = sum(get_total_credits_by_type(username).values())
    min_credits, max_credits = semester_ranges.get(semester, (None, None))
    if min_credits is None:
        return {"semester": semester, "taken_credits": taken, "recommended_range": None, "difference": None, "status": "unknown"}
    if taken < min_credits:
        diff = taken - min_credits
    elif taken > max_credits:
        diff = taken - max_credits
    else:
        diff = 0

    return {
        "semester": semester,
        "taken_credits": taken,
        "recommended_range": (min_credits, max_credits),
        "difference": diff
    }


# --- Example Usage ---
if __name__ == "__main__":
    from pprint import pprint

    # Example courses for credit_checker
    courses = [
        {"course": "AI Ethics", "credits": 3, "type": "required"},
        {"course": "Deep Learning", "credits": 4, "type": "optional"},
        {"course": "Reinforcement Learning", "credits": 3, "type": "optional"},
        {"course": "Intro to ML", "credits": 3, "type": "prerequisites"},
        {"course": "Advanced ML", "credits": 10, "type": "required"},
        {"course": "Vision Lab", "credits": 3, "type": "optional"},
    ]
    pprint(credit_checker(courses, gpa=13))
    pprint(user_credits_summary("Leila"))
    pprint(is_on_track("Leila", 4))
