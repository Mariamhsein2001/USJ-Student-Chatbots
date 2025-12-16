from collections import defaultdict
from copy import deepcopy
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from utils.course_eligibility import analyzing_eligibility
from utils.overlapping_times_checker import check_schedule_conflicts, map_courses_by_groups
from utils.utilities import parse_schedule,build_conflict_groups
from utils.db.db_utils import get_user_info

def get_user_conflict_groups(username: str):
        
    user = get_user_info(username)
    program = user["program"]

    # Analyze eligibility
    eligibility_result = analyzing_eligibility(username)

    # Parse all schedules before conflict checking
    eligible_courses = []
    for courses in eligibility_result.get("available_this_semester", {}).values():
        for c in courses:
            # Default group to "group_1" if missing
            group = c.get('group') or "group_1"
            eligible_courses.append({
                "course": f"{c['course']}",
                "group": group,
                "schedule": parse_schedule(c.get("schedule", {}))
            })

    # Map courses by actual group from the program
    mapped_courses = map_courses_by_groups(eligible_courses, program, user["current_semester"])
 
    # Check conflicts
    conflicts = check_schedule_conflicts(mapped_courses)
    
    # Build conflict pairs set
    conflict_pairs = set(f"{c1} vs {c2}" for c1, c2, *_ in conflicts)
    # Build actual conflict groups using clique-based merging
    conflict_groups = build_conflict_groups(conflict_pairs)

    return conflict_groups if conflict_groups else ["No schedule conflicts."]

def build_non_conflicting_schedule(courses, program, semester, max_schedules=20):
    """
    Expand schedules step by step starting from highest priority courses.
    Explore all possible group choices, prune conflicting ones.
    """
    priority_order = [
        "Required Previous",
        "UE Obligatoires",
        "UE Obligatoires pour l’option",
        "Optionnelle Fermée",
        "Optionnelle Ouverte"
    ]

    # Sort courses in priority order
    sorted_courses = []
    for p in priority_order:
        sorted_courses.extend([c for c in courses if c["type"] == p])

    schedules = [[]]  # start with empty

    for course in sorted_courses:
        new_schedules = []
        all_groups = map_courses_by_groups([course], program, semester)
    
        for sched in schedules:
            for g in all_groups:
                parsed_sched = parse_schedule(g.get("schedule") or {})
                candidate = {
                    "course": g["course"],
                    "code": course["code"],
                    "type": course["type"],
                    "group": g["group"],
                    "schedule": parsed_sched,
                    
                }
                if not check_schedule_conflicts(sched + [candidate]):
                    new_schedules.append(sched + [candidate])

        # Keep all valid branches (don’t overwrite like before)
        schedules = new_schedules if new_schedules else schedules

    # Deduplicate schedules
    unique = []
    seen = set()
    for s in schedules:
        key = tuple(sorted(c["code"] + "_" + c["group"] for c in s))
        if key not in seen:
            seen.add(key)
            unique.append(s)

    # Sort by length (prefer maximal schedules)
    unique.sort(key=len, reverse=True)

    # Label schedules
    result = {f"schedule_{i+1}": sched for i, sched in enumerate(unique[:max_schedules])}
    return result



def merge_schedules_dict_format(schedules_dict):
    """
    Merge schedules that differ by only one course's group,
    then remove exact duplicates.
    """
    schedule_list = list(schedules_dict.values())
    merged = []
    used = set()

    for i, sched1 in enumerate(schedule_list):
        if i in used:
            continue

        combined = deepcopy(sched1)
        variable_courses = defaultdict(list)

        for j, sched2 in enumerate(schedule_list[i+1:], start=i+1):
            if j in used:
                continue

            # Count differences in course group for the same course code
            diffs = 0
            diff_index = -1
            for idx, (c1, c2) in enumerate(zip(sched1, sched2)):
                if c1['code'] == c2['code'] and c1['group'] != c2['group']:
                    diffs += 1
                    diff_index = idx

            # Only one difference? merge groups
            if diffs == 1:
                variable_courses[diff_index].append(sched2[diff_index]['group'])
                used.add(j)

        # Apply merged groups
        for idx, groups in variable_courses.items():
            current_group = combined[idx]['group']
            combined[idx]['group'] = sorted(list(set([current_group] + groups)))

        merged.append(combined)

    # Remove exact duplicates
    unique_schedules = []
    seen = set()
    for sched in merged:
        key = tuple(sorted((c['code'], tuple(c['group']) if isinstance(c['group'], list) else c['group']) for c in sched))
        if key not in seen:
            unique_schedules.append(sched)
            seen.add(key)


    return unique_schedules

def merge_overlapping_groups(schedule):
    """
    Merge overlapping course groups across schedules
    while checking for actual schedule conflicts before merging.
    """
    merged_schedules = []

    for sched in schedule:
        merged = False

        for existing in merged_schedules:
            overlap = True

            # Prepare merged candidate (to test conflicts)
            tentative = deepcopy(existing)

            for c_new in sched:
                # Find matching course in existing schedule
                match = next((c for c in tentative if c["code"] == c_new["code"]), None)

                if match:
                    # Combine all groups but check each group schedule for conflicts
                    existing_groups = match["group"] if isinstance(match["group"], list) else [match["group"]]
                    new_groups = c_new["group"] if isinstance(c_new["group"], list) else [c_new["group"]]
                    valid_groups = []

                    for g in new_groups:
                        # Create a test candidate for this single group
                        test_course = deepcopy(c_new)
                        test_course["group"] = g
                        test_sched = tentative.copy()
                        test_sched = [x for x in test_sched if x["code"] != test_course["code"]] + [test_course]

                        # Only keep if no conflicts with any other courses
                        if not check_schedule_conflicts(test_sched):
                            valid_groups.append(g)

                    # If none of the new groups are valid, can't merge
                    if not valid_groups:
                        overlap = False
                        break

                    # Otherwise merge valid groups
                    match["group"] = sorted(list(set(existing_groups + valid_groups)))

                else:
                    # new course not in existing schedule — check conflicts with all
                    test_sched = tentative + [c_new]
                    if not check_schedule_conflicts(test_sched):
                        tentative.append(c_new)
                    else:
                        overlap = False
                        break

            if overlap:
                merged_schedules.remove(existing)
                merged_schedules.append(tentative)
                merged = True
                break

        if not merged:
            merged_schedules.append(sched)

    return merged_schedules


def finalize_non_conflicting_schedule(username: str, suggested_courses: list[dict]):
    """
    Takes LLM suggested courses (with code, name, type) and returns
    merged non-conflicting schedules with selected groups.
    """
    user = get_user_info(username)
    if not user:
        return {"error": f"User '{username}' not found."}

    program = user["program"]
    semester = user["current_semester"]

    # Prepare courses for schedule builder
    courses_for_schedule = [
        {"course": c["course"], "code": c["code"], "type": c.get("type", "")}
        for c in suggested_courses
    ]

    # Build all non-conflicting schedules
    schedules = build_non_conflicting_schedule(courses_for_schedule, program, semester)
   
    if not schedules:
        return {"error": "No non-conflicting schedule could be created with suggested courses."}
   
    merged_schedules = merge_schedules_dict_format(schedules)
   
    final_schedules = merge_overlapping_groups(merged_schedules)

    final_schedules_dict = {f"schedule_{i+1}": s for i, s in enumerate(final_schedules)}
    
    # --- Build schedule per group ---
   # Build one reference of all possible groups + schedules
    mapped_courses = map_courses_by_groups(courses_for_schedule, program, semester)

    course_group_map = {}
    for mc in mapped_courses:
        course = mc["course"]
        group = mc["group"]
        sched = parse_schedule(mc.get("schedule", {}))
        if course not in course_group_map:
            course_group_map[course] = {}
        course_group_map[course][group] = sched

    # --- Format output ---
    result = {}
    for i, sched in enumerate(final_schedules, start=1):
        formatted = []
        for course in sched:
            groups = course['group'] if isinstance(course['group'], list) else [course['group']]

            # Look up real schedules from course_group_map
            group_schedule_map = {}
            for g in groups:
                if course['course'] in course_group_map and g in course_group_map[course['course']]:
                    group_schedule_map[g] = course_group_map[course['course']][g]
                else:
                    group_schedule_map[g] = {}

            formatted.append({
                "course": course['course'],
                "code": course['code'],
                "type": course['type'],
                "group": groups,
                "schedule": group_schedule_map
            })
        result[f"schedule_{i}"] = formatted
    return result

# --- Main ---
if __name__ == "__main__":
    username = "Leila"
    conflict_groups = get_user_conflict_groups(username)

    user = get_user_info(username)
    program = user["program"]
    semester = user["current_semester"]

    courses = [
        {"course": "Electronique analogique", "code": "020ELAES1", "type": "Required Previous"},
        {"course": "Ethique et entreprise", "code": "020ETHES3", "type": "UE Obligatoires"},
        {"course": "Structures de données et algorithmes", "code": "020SDAES3", "type": "UE Obligatoires"},
        {"course": "Innovation and design thinking", "code": "020INDES2", "type": "UE Obligatoires"},
        {"course": "Traitement numérique du signal", "code": "020TNSES3", "type": "UE Obligatoires pour l’option"},
        {"course": "Systèmes embarqués", "code": "020SEMES3", "type": "Optionnelle Fermée"},
        {"course": "Architecture des ordinateurs", "code": "020AROES3", "type": "Optionnelle Fermée"}
        ]

    final_schedules = finalize_non_conflicting_schedule(username, courses)
    print(final_schedules)
    for sched in final_schedules.values():
        for c in sched:
            print(c['course'], c['group'])
        print("------")
