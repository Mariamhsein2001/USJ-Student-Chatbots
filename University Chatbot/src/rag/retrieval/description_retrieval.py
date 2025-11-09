
import json
import logging
from typing import Optional, List, Dict
from difflib import SequenceMatcher
logging.basicConfig(
    level=logging.INFO,  # Show INFO and above
    format="%(asctime)s - %(levelname)s - %(message)s",
)
def is_exact_match(course_name: str, title: str) -> bool:
    """Check if course_name exactly matches title (case-insensitive)."""
    return course_name.strip().lower() == title.strip().lower()


def is_fuzzy_match(course_name: str, title: str, min_similarity: float = 0.6) -> bool:
    """Check if course_name is similar enough to title."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, course_name.lower().strip(), title.lower().strip()).ratio() >= min_similarity


def find_courses_by_name_from_file(
    json_path: str,
    course_name: str,
    department_name: Optional[str] = None,
    program_name: Optional[str] = None,
    min_similarity: float = 0.6
) -> List[Dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    exact_results = []
    fuzzy_results = []

    departments_to_search = [department_name] if department_name and department_name in data else data.keys()

    for department in departments_to_search:
        dept_data = data.get(department, {})

        if isinstance(dept_data, list):
            courses = dept_data
            for course in courses:
                if is_exact_match(course_name, course["title"]):
                    exact_results.append({"department": department, "course": course})
                elif is_fuzzy_match(course_name, course["title"], min_similarity):
                    fuzzy_results.append({"department": department, "course": course})

        elif isinstance(dept_data, dict):
            programs_to_search = [program_name] if program_name and program_name in dept_data else dept_data.keys()
            for program in programs_to_search:
                courses = dept_data[program].get("courses", [])
                for course in courses:
                    if is_exact_match(course_name, course["title"]):
                        exact_results.append({"department": department, "program": program, "course": course})
                    elif is_fuzzy_match(course_name, course["title"], min_similarity):
                        fuzzy_results.append({"department": department, "program": program, "course": course})

    # fallback search in all departments if no exact match found
    if not exact_results:
        for department, dept_data in data.items():
            if department in departments_to_search:
                continue

            if isinstance(dept_data, list):
                courses = dept_data
            elif isinstance(dept_data, dict):
                courses = []
                for prog_info in dept_data.values():
                    courses.extend(prog_info.get("courses", []))
            else:
                continue

            for course in courses:
                if is_fuzzy_match(course_name, course["title"], min_similarity):
                    fuzzy_results.append({"department": department, "course": course})

    results = exact_results if exact_results else fuzzy_results

    logging.info(f"Results for course: {results}")
    return results



# --- Example usage ---
if __name__ == "__main__":
    json_file = "storage/data/course_descriptions/courses_by_department.json"
    course_to_search = "Programming for AI"
    department_to_search = "Département "  
    # program = "Master en Data Sciences"


    results = find_courses_by_name_from_file(
        json_file,
        course_to_search,
        department_name=department_to_search
    )

    if results:
        for res in results:
            print(f"Department: {res['department']}")
            if "program" in res:
                print(f"Program: {res['program']}")
            print("Course details:")
            for key, value in res["course"].items():
                print(f"  {key}: {value}")
            print("-" * 40)
        
    else:
        print(f"No courses found for '{course_to_search}'.")
