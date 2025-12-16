import sys
import os

from utils.db.db_utils import get_courses_taken_by_user, get_user_info
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import json
from collections import defaultdict
from utils.utilities import get_all_courses_by_program, trace_missing_prereqs,format_schedule

def analyze_course_eligibility(courses_by_semester, taken_codes, target_semester):
    """
    Determine which courses a student can take based on prerequisites.

    Args:
        courses_by_semester (dict): {semester: [course dicts]}.
        taken_codes (set/list): Completed course codes.
        target_semester (int/str): Semester to analyze.

    Returns:
        dict: {
            "courses_to_take": eligible course names,
            "available_this_semester": courses grouped by type,
            "unavailable_unmet_prereqs": blocked course names,
            "courses_to_take_by_semester": required past courses,
            "unmet_not_found": missing prerequisites not found
        }
    """
    available = []
    blocked = []
    prerequisites_needed = defaultdict(list)
    unmet_not_found = []

    # 1️.Handle current semester courses
    for course in courses_by_semester.get(target_semester, []):
        course_type = (course.get("type") or "").lower()
        sem_courses, missing = trace_missing_prereqs(
            course, taken_codes, courses_by_semester, target=course["course"]
        )
     
        if not sem_courses and not missing:
            available.append(course)
        else:
            blocked.append(course["course"])
            if "optionnel" in course_type or "optionnelles" in course_type:
                unmet_not_found.append({
                    "course": course["course"],
                    "code": course.get("code"),
                    "explanation": "Prerequisites unmet for this optional course — choose another."
                })
            else:
                unmet_not_found.extend(missing)
    # 2.Handle obligatory courses from previous semesters
    for sem, courses in courses_by_semester.items():
        if int(sem) >= int(target_semester):
            continue
        for course in courses:
            course_type = (course.get("type") or "").lower()
            if "ue obligatoires" not in course_type:
                continue
            if course["code"] in taken_codes:
                continue  

            # Only now check prerequisites
            sem_courses, missing = trace_missing_prereqs(
                course, taken_codes, courses_by_semester, target=course["course"]
            )
            
            if not sem_courses and not missing:
                available.append(course)
                prerequisites_needed[sem].append(course)
            else:
                # Add missing prerequisites if they exist
                for s, prereqs in sem_courses.items():
                    for prereq_course in prereqs:
                        if prereq_course["code"] not in taken_codes:
                            available.append(prereq_course)
                            prerequisites_needed[s].append(prereq_course)
                
                unmet_not_found.extend(missing)
           
    # 3.Deduplicate blocked courses
    blocked = list(dict.fromkeys(blocked))

    # 4.Deduplicate unmet_not_found (handle code-less entries too)
    seen_entries = set()
    deduped_nf = []

    for nf in unmet_not_found:
        # Convert the whole dict to a JSON string (sorted keys) for comparison
        nf_str = json.dumps(nf, sort_keys=True)
        if nf_str not in seen_entries:
            seen_entries.add(nf_str)
            deduped_nf.append(nf)


    # 5.Collect course names to take (only courses with fully satisfied prerequisites)
    course_names_to_take = list(dict.fromkeys([c["course"] for c in available]))

    # 6.Group available courses by type
    grouped_available = defaultdict(list)
    for c in available:
        c_copy = c.copy()
        c_copy["schedule"] = format_schedule(c.get("schedule"))
        grouped_available[c.get("type", "required")].append(c_copy)

    return {
        "courses_to_take": course_names_to_take,
        "available_this_semester": dict(grouped_available),
        "unavailable_unmet_prereqs": blocked,
        "courses_to_take_by_semester": dict(prerequisites_needed),
        "unmet_not_found": deduped_nf
    }


def reclassify_other_tracks(all_courses_by_semester, student_track):
    """
    Reclassify 'UE Obligatoires pour l’option' courses as 'Optionnelles Fermées'
    if the student has no track.

    Args:
        all_courses_by_semester (dict): {semester: [course dicts]}.
        student_track (str/None): Student's track.

    Returns:
        dict: Courses by semester with updated types.
    """
    student_track = student_track.strip().lower() if student_track else None
    new_semester_dict = {}

    for sem, courses in all_courses_by_semester.items():
        new_courses = []
        for c in courses:
            c_copy = c.copy()
            course_type = c_copy.get("type") or ""
            course_type_lower = course_type.lower()

            # Only reclassify if course is UE Obligatoires for an option AND student has no track
            if "ue obligatoires pour l’option" in course_type_lower and not student_track in course_type_lower :
                c_copy["type"] = "Optionnelles Fermées"

            new_courses.append(c_copy)

        new_semester_dict[sem] = new_courses

    return new_semester_dict

def analyzing_eligibility(username): 
    user = get_user_info(username)
    if not user:
        print(f"User '{username}' not found.")
        return
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
    return result

def main():
    username = "Leila"
    result = analyzing_eligibility(username)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
