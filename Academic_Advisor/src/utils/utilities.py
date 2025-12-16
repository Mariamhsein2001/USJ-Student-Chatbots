# utils/utils.py

from datetime import datetime
from itertools import combinations
import re
from collections import defaultdict
from utils.db.db_utils import get_academic_plan_courses, get_courses_by_program_and_semester

def check_course_prerequisite(course, taken_codes):
    """
    Check which prerequisites of a course are satisfied or unmet.

    Args:
        course (dict): Course dictionary containing 'prerequisites'.
        taken_codes (list[str]): List of course codes the user has taken.

    Returns:
        tuple[list[str], list[str]]: (satisfied_codes, unmet_codes)
    """
    prereq_text = course.get("prerequisites") or ""
    taken_set = set(taken_codes)
    satisfied_codes = []
    unmet_codes = []

    text = prereq_text.lower().replace(";", ",").replace(" et ", ",")
    and_groups = [g.strip() for g in text.split(",") if g.strip()]
    course_code_pattern = r"\b\d{3}[A-Z0-9]{6}\b"

    for group in and_groups:
        or_parts = [p.strip() for p in re.split(r"\bou\b", group)]
        codes = []
        for part in or_parts:
            raw_codes = re.findall(course_code_pattern, part.upper())
            codes.extend([code.strip(".,;: ") for code in raw_codes])

        if not codes:
            continue

        if any(code in taken_set for code in codes):
            satisfied_codes.extend([code for code in codes if code in taken_set])
        else:
            unmet_codes.extend(codes)

    return list(set(satisfied_codes)), list(set(unmet_codes))


def group_courses_by_title(courses_list):
    """
    Group courses by their title, organizing by course groups.

    Args:
        courses_list (list[dict]): List of course dictionaries.

    Returns:
        dict: Grouped courses by title with subgroups.
    """
    grouped = defaultdict(lambda: {"groups": {}})
    for course in courses_list:
        title = course["course"]
        group = course["group"]
        grouped[title]["code"] = course.get("code")
        grouped[title]["credits"] = course.get("credits")
        grouped[title]["prerequisites"] = course.get("prerequisites")
        grouped[title]["groups"][group] = {
            "instructor": course["instructor"],
            "type": course.get("type"),
            "extra_info": course.get("extra_info"),
            "schedule": course.get("schedule"),
        }
    return grouped


def get_course_description(course: dict) -> str:
    """
    Generate a readable course description from its fields.

    Args:
        course (dict): Course dictionary containing title, prerequisites, credits, etc.

    Returns:
        str: Formatted, human-readable course description.
    """
    name = course.get("course", "Unnamed")
    prereqs = course.get("prerequisites")
    unlocks = course.get("unlocks", [])
    course_type = course.get("type")
    extra = course.get("extra_info")
    credits = course.get("credits")

    parts = []
    if credits:
        parts.append(f"{credits} credits")
    if course_type:
        parts.append(f"Type: {course_type}")
    if prereqs and prereqs.lower() not in ("rien", "none", ""):
        parts.append(f"Requires: {prereqs}")
    if unlocks:
        parts.append(f"Unlocks: {', '.join(unlocks)}")
    if extra and extra.lower() != "none":
        parts.append(f"Note: {extra}")

    if not parts:
        return f"{name}: No additional info available."
    return f"{name}: " + " | ".join(parts)



def get_all_courses_by_program(program_name: str, current_semester: int) -> dict:
    """
    Fetches all available courses grouped by semester for a given program,
    limited to semesters with the same parity (odd/even) up to current_semester.

    Args:
        program_name (str): Name of the program (e.g., "Génie Électrique").
        current_semester (int): The user's current semester.


    Returns:
        dict: {semester_number_str: [course_dicts]} where semester ∈ [1, current_semester]
              and has same parity (odd/even) as current_semester.
    """

    is_even = current_semester % 2 == 0
    semesters = [
        sem for sem in range(1, current_semester + 1)
        if (sem % 2 == 0) == is_even
    ]

    return {
        str(sem): get_courses_by_program_and_semester(program_name, sem)
        for sem in semesters
    }

def parse_time(t):
    return datetime.strptime(t, "%H:%M")

def expand_weeks(weeks_str):
    if not weeks_str or weeks_str.strip().lower() == "all":
        return set(range(1, 14))  # weeks 1 to 13

    result = set()
    parts = [w.strip() for w in weeks_str.split(",") if w.strip()]
    for part in parts:
        if part.lower() == "impaires":
            result.update(week for week in range(1, 14) if week % 2 == 1)
        elif part.lower() == "paires":
            result.update(week for week in range(1, 14) if week % 2 == 0)
        elif "-" in part:
            try:
                start, end = map(int, part.split("-"))
                result.update(range(start, end + 1))
            except ValueError:
                pass
        else:
            try:
                result.add(int(part))
            except ValueError:
                pass
    return result


def trace_missing_prereqs(course, taken_codes, all_courses_by_sem, target=None, visited=None):
    """
    Recursively find unmet prerequisites in past semesters.
    Returns:
        - missing_by_semester: dict of semester → list of missing prerequisite course details
        - not_found: list of missing prerequisites not offered in any semester
    """
    missing_by_semester = defaultdict(list)
    not_found = []

    # Track visited to avoid infinite loops (e.g., circular prereqs)
    if visited is None:
        visited = set()

    # Prevent re-checking the same course
    if course["code"] in visited:
        return {}, []
    visited.add(course["code"])

    # Check unmet prereqs for this course
    _, unmet = check_course_prerequisite(course, taken_codes)
    if not unmet:
        return {}, []

    target = target or course["course"]

    for code in unmet:
        found = False
        for sem, course_list in all_courses_by_sem.items():
            for c in course_list:
                if c.get("code") == code:
                    found = True
                    # Recurse on this prerequisite
                    children, not_found_children = trace_missing_prereqs(
                        c, taken_codes, all_courses_by_sem, target, visited
                    )
                    # Merge child results
                    for s, items in children.items():
                        missing_by_semester[s].extend(items)

                    # Add current prerequisite (leaf or chain element)
                    prereq_entry = {
                        "course": c["course"],
                        "code": c["code"],
                        "instructor": c.get("instructor"),
                        "schedule": c.get("schedule"),
                        "extra_info": c.get("extra_info"),
                        "prerequisites": c.get("prerequisites"),
                        "unlocks": [course["course"]],
                        "final_target": [target],
                        "explanation": (
                            f"You must take '{c['course']}' (code {c['code']}) "
                            f"to unlock '{course['course']}', which is required for '{target}'."
                        )
                    }

                    # Avoid duplicate entries
                    if prereq_entry not in missing_by_semester[sem]:
                        missing_by_semester[sem].append(prereq_entry)

                    not_found.extend(not_found_children)

        if not found:
            not_found.append({
                "code": code,
                "explanation": (
                    f"'{code}' is required for '{course['course']}' → '{target}', "
                    f"but not offered in any semester."
                )
            })

    return missing_by_semester, not_found


def format_schedule(schedule_dict):
    """
    Converts schedule dictionary to a concise human-readable string.
    """
    if not schedule_dict:
        return ""

    day_strs = []
    for day, slots in schedule_dict.items():
        slot_strs = []
        for slot in slots:
            weeks = slot.get("weeks", "all")
            if weeks.lower() == "all":
                weeks_str = "all weeks"
            else:
                weeks_str = f"week {weeks}"
            start = slot.get("start_time", "?")
            end = slot.get("end_time", "?")
            slot_strs.append(f"{start}-{end} ({weeks_str})")
        day_str = f"{day} " + ", ".join(slot_strs)
        day_strs.append(day_str)
    return "; ".join(day_strs)



def parse_schedule(schedule):
    parsed = {}
    if isinstance(schedule, dict):
        for day, sessions in schedule.items():
            parsed[day] = []
            for s in sessions:
                parsed[day].append({
                    "start_time": s["start_time"],
                    "end_time": s["end_time"],
                    "weeks": s.get("weeks", "all")
                })
    elif isinstance(schedule, str):
        # Split by semicolon or comma
        parts = [p.strip() for p in schedule.replace(";", ",").split(",") if p.strip()]
        for part in parts:
            try:
                day_time, *rest = part.split("(")
                day, times = day_time.strip().split(" ", 1)
                start, end = times.split("-")
                weeks = rest[0].replace(")", "").strip() if rest else "all"
                parsed.setdefault(day, []).append({
                    "start_time": start.strip(),
                    "end_time": end.strip(),
                    "weeks": weeks
                })
            except:
                continue
    return parsed

def build_conflict_groups(conflict_pairs):
    """
    Build groups where every course in the group conflicts with every other course.
    """
    # Start with pairwise conflicts as initial cliques
    cliques = [set(pair.split(" vs ")) for pair in conflict_pairs]

    merged = True
    while merged:
        merged = False
        new_cliques = []
        used = [False] * len(cliques)
        for i, c1 in enumerate(cliques):
            if used[i]:
                continue
            for j, c2 in enumerate(cliques[i+1:], start=i+1):
                if used[j]:
                    continue
                # Merge only if every element in c1 conflicts with every element in c2
                if all(
                    (f"{a} vs {b}" in conflict_pairs or f"{b} vs {a}" in conflict_pairs)
                    for a, b in combinations(c1.union(c2), 2)
                ):
                    c1 = c1.union(c2)
                    used[j] = True
                    merged = True
            new_cliques.append(c1)
            used[i] = True
        cliques = new_cliques

    # Convert sets to sorted lists and remove duplicates
    seen = set()
    result = []
    for g in cliques:
        g_sorted = tuple(sorted(g))
        if g_sorted not in seen:
            seen.add(g_sorted)
            result.append(list(g_sorted))

    return result

def format_courses_for_llm(recommendations: list[dict], include_description: bool = True) -> str:
    """
    Compact, LLM-friendly format:
    First line defines the schema once. Each subsequent line contains values only.
    """
    schema = "code,title,type,credits,weight,description"
    lines = [f"Schema: {schema}"]

    for c in recommendations:
        # Convert all values to string safely
        values = [
            str(c.get("code") or ""),
            str(c.get("title") or ""),
            str(c.get("type") or ""),
            str(c.get("credits") or ""),
            str(c.get("weight") or ""),
        ]
        # Handle optional description
        if include_description:
            desc = c.get("description")
            if desc:
                desc = desc[:100] + "..." if len(desc) > 50 else desc
            else:
                desc = ""
            values.append(desc)
        else:
            values.append("") 

        lines.append(",".join(values)) 
    
    return "\n ".join(lines)


def format_courses_for_credits(recommendations: list[dict]) -> str:
    lines = []
    for c in recommendations:
        course_type = c.get("type", "None")  # <-- Added type
        lines.append(
            f"{c['title']} | Type: {course_type} | Credits: {c['credits']} | "
        )
    return "\n".join(lines)

def format_schedule_for_llm(schedules: dict) -> dict:
    """
    Converts finalized schedules into a clean, LLM-friendly string format.
    """
    formatted_schedules = {}

    for sched_name, sched in schedules.items():
        lines = []
        for c in sched:
            course_name = c.get("course", "")
            code = c.get("code", "")
            ctype = c.get("type", "")
            lines.append(f"Course: {course_name} ({code}) | Type: {ctype}")

            for group in c.get("group", []):
                group_schedule = c.get("schedule", {}).get(group, {})
                lines.append(f"  Group: {group}")
                for day, sessions in group_schedule.items():
                    session_strs = [
                        f"{s.get('start_time','')}-{s.get('end_time','')} [{s.get('weeks','all')}]"
                        for s in sessions
                    ]
                    lines.append(f"    {day}: {', '.join(session_strs)}")
        
        formatted_schedules[sched_name] = "\n".join(lines)

    return formatted_schedules

def clean_gemini_json(response_text: str) -> str:
    """
    Remove markdown ```json blocks and extra whitespace to get pure JSON.
    """
    # Remove ```json or ``` at start/end
    cleaned = re.sub(r'^```json\s*', '', response_text)
    cleaned = re.sub(r'```$', '', cleaned.strip())
    return cleaned

def summarize_past_courses(courses: list[dict]) -> str:
    if not courses:
        return "The student has no recorded passed or failed courses yet."
    passed = [c for c in courses if c["status"] == "passed"]
    failed = [c for c in courses if c["status"] == "failed"]
    def list_courses(courses):
        return "\n".join(f"- {c['code']} - {c['title']} | Grade: {c['grade']}" for c in courses)
    summary = f"""
## Academic History Summary
### Passed Courses ({len(passed)}):
{list_courses(passed) if passed else 'None'}

### Failed Courses ({len(failed)}):
{list_courses(failed) if failed else 'None'}
""".strip()
    return summary


def load_rules_from_file(filepath: str ) -> str:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            rules_content = f.read()
            return rules_content.strip()
    except Exception as e:
        print(f"Warning: Could not load rules file from {filepath}. Using default generic rules. Error: {e}")


def all_courses(username: str):
    """
    Fetch academic plan courses for a user's program, grouped by semester.

    Returns a dictionary: {semester_number: [courses]}
    Each course is a dict: {"code", "title", "credits"}
    """
    courses = get_academic_plan_courses(username)
    if not courses:
        return {}

    courses_by_semester = {}
    for course in courses:
        sem = course["semester"]
        courses_by_semester.setdefault(sem, []).append({
            "code": course["code"],
            "title": course["title"],
            "credits": course["credits"],
            "course_type": course["course_type"]
        })

    return dict(sorted(courses_by_semester.items()))
