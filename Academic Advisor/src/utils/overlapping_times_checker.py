
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from utils.db.db_utils import get_user_info
from utils.utilities import get_all_courses_by_program,parse_time,expand_weeks


# --- Mapping courses to groups ---
def map_courses_by_groups(courses_to_map, program, semester):
    data = get_all_courses_by_program(program, semester)
    results = []

    for entry in courses_to_map:
        course_name = entry.get("course")
        input_group = entry.get("group") or "group_1"  # ensure default at input level

        for semester_courses in data.values():
            for course_entry in semester_courses:
                if course_entry.get("course") == course_name:
                    # Always default group if missing in DB
                    actual_group = course_entry.get("group") or "group_1"

                    # Only filter if user explicitly asked for another group
                    if "group" in entry and entry["group"] and entry["group"] != actual_group:
                        continue

                    results.append({
                        "course": course_name,
                        "group": actual_group,
                        "schedule": course_entry.get("schedule", {})
                    })

    return results

def check_schedule_conflicts(courses):
    conflicts = []
    for i in range(len(courses)):
        c1 = courses[i]
        for j in range(i + 1, len(courses)):
            c2 = courses[j]

            common_days = set(c1["schedule"]) & set(c2["schedule"])
 
            for day in common_days:
                for slot1 in c1["schedule"][day]:
                    for slot2 in c2["schedule"][day]:
                        start1 = parse_time(slot1["start_time"])
                        end1 = parse_time(slot1["end_time"])
                        start2 = parse_time(slot2["start_time"])
                        end2 = parse_time(slot2["end_time"])

                        if start1 < end2 and start2 < end1:
                
                            weeks1 = expand_weeks(slot1.get("weeks", "all"))
                            weeks2 = expand_weeks(slot2.get("weeks", "all"))
                          
                            overlap_weeks = weeks1 & weeks2
                            if overlap_weeks:
                                conflicts.append((
                                    f"{c1['course']}",
                                    f"{c2['course']}",
                                    day,
                                    f"{slot1['start_time']}-{slot1['end_time']} ({slot1.get('weeks')})",
                                    f"{slot2['start_time']}-{slot2['end_time']} ({slot2.get('weeks')})",
                                    sorted(list(overlap_weeks))
                                ))
    return conflicts



# --- Main ---
def main():
    username = 'Leila'
    user_info = get_user_info(username)
    program = user_info["program"]
    semester = user_info["current_semester"]

    courses_to_map = [
        {'code': '020CMPES5', 'course': 'Comptabilité', 'type': 'UE Obligatoires'},
        {'code': '020GLOES5', 'course': 'Génie logiciel', 'type': 'UE Obligatoires pour l’option'}
    ]

    # Default any course without a group to group_1
    for c in courses_to_map:
        if "group" not in c or not c["group"]:
            c["group"] = "group_1"

    mapped_courses = map_courses_by_groups(courses_to_map, program, semester)
    
    print("\n📋 Mapped Courses with Groups and Schedule:")
    import pprint
    pprint.pprint(mapped_courses)

    # Check conflicts
    conflicts = check_schedule_conflicts(mapped_courses)
    if conflicts:
        print("\n Schedule Conflicts Found:")
        for c1, c2, day, time1, time2, weeks in conflicts:
            print(f" - {c1} vs {c2} on {day} | {time1} ↔ {time2} | Weeks: {weeks}")
    else:
        print("\n No schedule conflicts.")

if __name__ == "__main__":
    main()

