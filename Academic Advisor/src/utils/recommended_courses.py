import json
import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.utilities import (
    get_all_courses_by_program,
    check_course_prerequisite
)
from utils.course_eligibility import analyze_course_eligibility, reclassify_other_tracks
from utils.db.db_utils import  get_course_description_by_code,get_user_info,get_courses_taken_by_user

restricted_courses = [
        "Économie de l’entreprise",
        "Management opérationnel",
        "Marketing",
        "Quality management",
        "Strategic planning",
        "Work ready now",
        "Logistics and supply chain management",
        "Financial markets and institutions",
        "Economie de l'entreprise"
    ]

def get_courses_evaluate(username):
    user = get_user_info(username)
    semester = str(user["current_semester"])
    user_id = user["user_id"]
    taken_courses = get_courses_taken_by_user(user_id)
    taken_codes = [c["code"] for c in taken_courses]

    all_courses_by_semester = get_all_courses_by_program(user['program'], user["current_semester"])
    all_courses_by_semester = reclassify_other_tracks(
    all_courses_by_semester,
    student_track=user.get("track")
        )

    result = analyze_course_eligibility(all_courses_by_semester, taken_codes, semester)
    courses_to_take_titles = result.get("courses_to_take", [])

    # Flatten with semester info
    all_courses_flat = []
    for sem, sem_courses in all_courses_by_semester.items():
        for course in sem_courses:
            course["semester_offered"] = int(sem)
            all_courses_flat.append(course)

    courses_to_take_full = []
    titles_set = set(courses_to_take_titles)
    for course in all_courses_flat:
        if course.get("course") in titles_set:
            course["availability"] = "current" if course["semester_offered"] == int(semester) else "previous/need to take as it is a prerequiste"
            courses_to_take_full.append(course)

    return courses_to_take_full

def get_importance(course_type: str) -> float:
    mapping = {
        "UE Obligatoires": 4,
        "UE Obligatoires pour l’option-Génie Logiciel":3,
        "UE Obligatoires pour l’option-Réseaux de Télécommunications":3,
        "Optionnelles Fermées": 2,
        "Optionnels Ouvertes": 1,
    }
    return mapping.get(course_type, 1)

def get_difficulty(course: dict, user_semester: int = 1) -> float:
    difficulty = 1
    reasons = []

    credits = course.get('credits') or 0
    if credits >= 4:
        difficulty += 1
        reasons.append("High credit course")

    prereq_text = course.get("prerequisites") or ""
    prereq_count = len(re.findall(r"\d{3}[A-Z0-9]{6}", prereq_text))
    if prereq_count >= 2:
        difficulty += 2
        reasons.append("Multiple prerequisites")

    course_title = course.get("course", "").lower()
    if any(kw in course_title for kw in ['math', 'analyse', 'phys', 'syst', 'thermo']):
        difficulty += 1
        reasons.append("Theoretical/technical content detected")

    return min(difficulty, 5), reasons

def recommend_weight(gpa, difficulty, importance, prereqs_met: bool) -> float:
    if not prereqs_met:
        return 0
    if gpa >= 16 :
        return 1.2 * importance + 0.8 * difficulty
    elif gpa >= 14:
        return importance + 0.5 * difficulty
    elif gpa >= 12:
        return 1.5 * importance - 0.6 * difficulty
    else:
        return 2.0 * importance - 0.8 * difficulty

def build_reasoning(course, gpa, importance, difficulty, prereqs_met, difficulty_reasons):
    reasons = []

    # Prerequisite status
    if not prereqs_met:
        reasons.append("Unmet prerequisites.")
    else:
        reasons.append("Prerequisites satisfied.")

    # Course importance explanation
    if importance == 4:
        reasons.append("Core course (Obligatoire) → high priority.")
    elif importance == 3:
        # Include the track if available
        track = course.get("type", "")
        reasons.append(f"UE Obligatoires pour l’option ({track}) → important restricted elective.")
    elif importance == 2:
        reasons.append("Restricted elective (Optionnelle Fermée) → medium priority.")
    else:
        reasons.append("Open elective (Optionnelle Ouverte) → lower priority.")

    # Difficulty factors
    if difficulty_reasons:
        reasons.append("Difficulty factors: " + ", ".join(difficulty_reasons))

    # Combine into single string
    return " ".join(reasons)


def recommend_courses_for_user(username: str) -> list[dict]:
    user_info = get_user_info(username)
    if not user_info:
        raise ValueError(f"User '{username}' not found.")
    
    current_semester = user_info.get("current_semester", 1)
    taken_courses = get_courses_taken_by_user(user_info["user_id"])
    taken_codes = [c["code"] for c in taken_courses]
    offered_courses = get_courses_evaluate(username)

    # Remove duplicate courses based on 'code' or 'title'
    seen_courses = set()
    unique_offered_courses = []
    for course in offered_courses:
        key = course.get("code") or course.get("course")
        if key and key not in seen_courses:
            seen_courses.add(key)
            unique_offered_courses.append(course)

    if current_semester == 1:
        return [
            {
                "title": course["course"],
                "code": course.get("code"),
                "credits": 2 if any(rc.lower() == course["course"].lower() for rc in restricted_courses) 
                        else course.get("credits", "None"),
                "type": "Optionnelles Fermées" if any(rc.lower() == course["course"].lower() for rc in restricted_courses) 
                        else course.get("type", "None"),
                "description": get_course_description_by_code(course.get("code")),
            }
            for course in unique_offered_courses
        ]    # Otherwise: Do full recommendation with weights
    recommendations = []


    for course in unique_offered_courses:
        _, unmet = check_course_prerequisite(course, taken_codes)
        prereqs_met = not unmet
        
        # --- New condition: force type for specific courses ---
        course_title = course.get("course", "")
        if any(rc.lower() == course_title.lower() for rc in restricted_courses):
            course_type = "Optionnelles Fermées"
        else:
            course_type = course.get("type", "None")
        
        importance = get_importance(course_type)
        difficulty_score, difficulty_reasons = get_difficulty(course, current_semester)
        weight = recommend_weight(user_info.get("gpa", 10), difficulty_score, importance, prereqs_met)
        
        # --- Adjust weight for prerequisites or previous semester courses ---
        # 1. If course is a prerequisite for other courses not yet taken
        if course.get("code"):
            for other_course in unique_offered_courses:
                other_prereqs = other_course.get("prerequisites") or ""
                if course["code"] in re.findall(r"\d{3}[A-Z0-9]{6}", other_prereqs):
                    weight += 1.5  # boost weight for being a prereq

        # 2. If course was offered in a previous semester
        if course.get("semester_offered", current_semester) < current_semester:
            weight += 1.0  # boost for previous semester

        recommendations.append({
            "title": course["course"],
            "code": course.get("code"),
            "credits": course.get("credits") or 2,
            "type": course_type,
            "instructor" : course.get("instructor"),
            "importance": importance,
            "difficulty": difficulty_score,
            "prereqs_met": prereqs_met,
            "weight": round(weight, 2),
            "availability": course.get("availability", "unknown"),
            "description": get_course_description_by_code(course.get("code")),
            "reasoning": build_reasoning(course, user_info.get("gpa", 10), importance, difficulty_score, prereqs_met, difficulty_reasons)
        })

    recommendations.sort(key=lambda x: x["weight"], reverse=True)
    return recommendations


if __name__ == "__main__":
    try:
        recs = recommend_courses_for_user("Celine")
        print(json.dumps(recs, ensure_ascii=False, indent=2))
    except ValueError as e:
        print(str(e))
