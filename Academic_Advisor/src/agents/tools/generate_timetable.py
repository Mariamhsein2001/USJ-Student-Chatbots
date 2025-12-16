
from collections import defaultdict

def parse_time(t):
    return int(t.split(":")[0]) * 60 + int(t.split(":")[1])

def combine_course_schedules(courses):
    combined = defaultdict(list)
    
    for course in courses:
        course_name = course.get("course", "")
        group = course.get("group", "")
        schedule = course.get("schedule", {})

        if not isinstance(schedule, dict):
            raise ValueError(f"Invalid schedule format for course: {course_name}")

        # Flatten nested group schedules if necessary
        flat_schedule = {}
        for key, val in schedule.items():
            if isinstance(val, dict):  # nested by group
                for day, sessions in val.items():
                    flat_schedule.setdefault(day, []).extend(sessions)
            else:
                flat_schedule.setdefault(key, []).extend(val)
        
        # Process each day
        for day, sessions in flat_schedule.items():
            for sess in sessions:
                enriched = sess.copy()
                enriched["course"] = course_name
                enriched["group"] = group
                combined[day].append(enriched)
    return dict(combined)

def generate_timetable(courses):
    combined = combine_course_schedules(courses)

    # Define fixed 1h15 time blocks
    time_blocks = [
        ("08:00", "09:15"),
        ("09:30", "10:45"),
        ("11:00", "12:15"),
        ("13:30", "14:45"),
        ("15:00", "16:15"),
        ("16:30", "17:45"),
        ("18:00", "19:15"),
    ]
    block_minutes = [(parse_time(s), parse_time(e)) for s, e in time_blocks]

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Initialize empty grid
    grid = {day: [""] * len(time_blocks) for day in days}

    # Helper to build label
    def make_label(session):
        parts = [f"<b>{session.get('course','')}</b>"]
        grp = session.get("group")
        stype = session.get("session_type")
        weeks = session.get("weeks","")
        extras = []
        if grp:
            extras.append(f"[{grp}]")
        if stype:
            extras.append(f"({stype})")
        if weeks and weeks != "all":
            extras.append(f"<small>Week: {weeks}</small>")
        if extras:
            parts.append("<br>".join(extras))
        return "<br>".join(parts)

    # Fill grid (multi-block sessions supported)
    for day in days:
        for session in combined.get(day, []):
            start = parse_time(session.get("start_time"))
            end = parse_time(session.get("end_time"))
            label = make_label(session)
            # find all overlapping time slots
            overlapping = []
            for i, (bstart, bend) in enumerate(block_minutes):
                if start < bend and end > bstart:
                    overlapping.append(i)

            if not overlapping:
                # if nothing matches, place in first empty slot
                for i in range(len(time_blocks)):
                    if not grid[day][i]:
                        grid[day][i] = label
                        break
                continue

            # assign label in first block, mark continuation in subsequent ones
            first = overlapping[0]
            if grid[day][first]:
                grid[day][first] += "<br><hr>" + label
            else:
                grid[day][first] = label

            for cont_idx in overlapping[1:]:
                cont_marker = "<span style='color:gray;'>↳ cont</span>"
                if grid[day][cont_idx]:
                    grid[day][cont_idx] += "<br><hr>" + cont_marker
                else:
                    grid[day][cont_idx] = cont_marker

    # Generate HTML table
    html = [
        "<h3>🗓️ Timetable</h3>",
        "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%; text-align: center; font-family: sans-serif;'>",
        "<thead style='background-color: #f2f2f2;'><tr><th>Time</th>" +
        "".join(f"<th>{day}</th>" for day in days) + "</tr></thead><tbody>"
    ]

    for i, (start, end) in enumerate(time_blocks):
        html.append("<tr>")
        html.append(f"<td><b>{start}–{end}</b></td>")
        for day in days:
            cell = grid[day][i]
            html.append(f"<td style='vertical-align: top;'>{cell}</td>")
        html.append("</tr>")

    html.append("</tbody></table>")
    return "\n".join(html)


if __name__ == "__main__":
    courses = [
        {'group': 'group_2', 'schedule': {'Lundi': [{'start_time': '13:30', 'end_time': '16:15', 'weeks': 'all'}],
                                          'Mercredi': [{'start_time': '13:30', 'end_time': '16:15', 'weeks': 'paires'}]},
         'course': 'Electronique analogique'},
        {'group': 'group_1', 'schedule': {'Vendredi': [{'start_time': '13:30', 'end_time': '16:15', 'weeks': 'all'}]},
         'course': 'Ethique et entreprise'},
        {'group': 'group_2', 'course': 'Structures de données et algorithmes',
         'schedule': {'Mardi': [{'start_time': '08:00', 'end_time': '10:45', 'weeks': 'all'}]}},
        {'group': 'group_2', 'course': 'Innovation and design thinking',
         'schedule': {'Mercredi': [{'start_time': '16:30', 'end_time': '19:15', 'weeks': 'paires'}]}},
        {'group': 'group_1', 'schedule': {'Vendredi': [{'start_time': '09:30', 'end_time': '12:15', 'weeks': 'all'}]},
         'course': 'Traitement numérique du signal'},
        {'group': 'group_1', 'course': 'Introduction à la science des données',
         'schedule': {'Lundi': [{'start_time': '16:30', 'end_time': '19:15', 'weeks': 'all'}]}},
        {'group': 'group_1', 'schedule': {'Vendredi': [{'start_time': '16:30', 'end_time': '19:15', 'weeks': 'all'}]},
         'course': 'Programmation pour le WEB'}
    ]

    html_output = generate_timetable(courses)
    print(html_output)
