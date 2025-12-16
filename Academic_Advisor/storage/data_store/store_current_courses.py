import sqlite3
import json
import re

# Connect to the SQLite database
conn = sqlite3.connect("storage/data_store/advising.db")
cursor = conn.cursor()

# === Create tables ===
cursor.executescript("""
DROP TABLE IF EXISTS course_time_mappings;
DROP TABLE IF EXISTS time_slots;
DROP TABLE IF EXISTS instructors_courses_provided;
DROP TABLE IF EXISTS courses_provided;
DROP TABLE IF EXISTS instructors;
""")

cursor.executescript("""
CREATE TABLE IF NOT EXISTS instructors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS courses_provided (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    raw_course_name TEXT NOT NULL,
    program_id INTEGER NOT NULL,
    semester INTEGER NOT NULL,
    group_name TEXT NOT NULL,
    extra_info TEXT,
    course_type TEXT,
    FOREIGN KEY(course_id) REFERENCES courses(course_id),
    FOREIGN KEY(program_id) REFERENCES programs(id)
);

CREATE TABLE IF NOT EXISTS instructors_courses_provided (
    instructor_id INTEGER NOT NULL,
    provided_id INTEGER NOT NULL,
    FOREIGN KEY (instructor_id) REFERENCES instructors(id),
    FOREIGN KEY (provided_id) REFERENCES courses_provided(id),
    PRIMARY KEY (instructor_id, provided_id)
);

CREATE TABLE IF NOT EXISTS time_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    week_day TEXT NOT NULL,
    weeks TEXT,
    session_type TEXT,
    UNIQUE(start_time, end_time, week_day, weeks, session_type)
);

CREATE TABLE IF NOT EXISTS course_time_mappings (
    provided_id INTEGER NOT NULL,
    time_slot_id INTEGER NOT NULL,
    FOREIGN KEY(provided_id) REFERENCES courses_provided(id),
    FOREIGN KEY(time_slot_id) REFERENCES time_slots(id),
    PRIMARY KEY (provided_id, time_slot_id)
);
""")
conn.commit()
# Add course_type column to courses_provided if it doesn't exist
def ensure_course_type_column_in_courses_provided(cursor):
    cursor.execute("PRAGMA table_info(courses_provided)")
    columns = [col[1] for col in cursor.fetchall()]
    if "course_type" not in columns:
        print("Adding column 'course_type' to courses_provided...")
        cursor.execute("ALTER TABLE courses_provided ADD COLUMN course_type TEXT")
        print("Column added.")
    else:
        print("'course_type' column already exists.")

ensure_course_type_column_in_courses_provided(cursor)
# === Load the schedule JSON ===
with open("storage/data/grouped_courses_by_program_DEM_S1.json", "r", encoding="utf-8") as f:
    schedule_data = json.load(f)

# Weekday mapping from English to French
weekday_map = {
    "Monday": "Lundi",
    "Tuesday": "Mardi",
    "Wednesday": "Mercredi",
    "Thursday": "Jeudi",
    "Friday": "Vendredi",
    "Saturday": "Samedi",
    "Sunday": "Dimanche"
}

# === Helper functions ===
def get_program_id(program_name):
    cursor.execute("SELECT id FROM programs WHERE name = ?", (program_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_course_id_by_title(title):
    cursor.execute("SELECT course_id FROM courses WHERE title = ?", (title,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_course_type_by_course_id(course_id):
    if not course_id:
        return None
    cursor.execute("SELECT course_type FROM courses WHERE course_id = ?", (course_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_or_create_instructor_id(name):
    name = name.strip()
    cursor.execute("SELECT id FROM instructors WHERE name = ?", (name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    cursor.execute("INSERT INTO instructors (name) VALUES (?)", (name,))
    conn.commit()
    return cursor.lastrowid

def insert_course_provided(course_id, raw_course_name, program_id, semester, group_name, extra_info):
    course_type = get_course_type_by_course_id(course_id)
    cursor.execute("""
        INSERT INTO courses_provided (
            course_id, raw_course_name, program_id, semester, group_name, extra_info, course_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (course_id, raw_course_name, program_id, semester, group_name, extra_info, course_type))
    conn.commit()
    return cursor.lastrowid

def insert_instructors_for_course(provided_id, instructor_names):
    for name in instructor_names:
        instructor_id = get_or_create_instructor_id(name)
        cursor.execute("""
            INSERT OR IGNORE INTO instructors_courses_provided (instructor_id, provided_id)
            VALUES (?, ?)
        """, (instructor_id, provided_id))
    conn.commit()

def insert_slot_and_map(provided_id, slot):
    start_time = slot.get("start_time")
    end_time = slot.get("end_time")
    week_day = slot.get("week_day")

    if week_day in weekday_map:
        week_day = weekday_map[week_day]

    if not start_time or not end_time or not week_day:
        print(f"[WARNING] Skipping invalid slot (missing start_time/end_time/week_day): {slot}")
        return

    cursor.execute("""
        INSERT OR IGNORE INTO time_slots (start_time, end_time, week_day, weeks, session_type)
        VALUES (?, ?, ?, ?, ?)
    """, (
        start_time, end_time, week_day,
        slot.get("weeks"), slot.get("session_type")
    ))
    conn.commit()

    cursor.execute("""
        SELECT id FROM time_slots
        WHERE start_time = ? AND end_time = ? AND week_day = ? AND weeks IS ? AND session_type IS ?
    """, (
        start_time, end_time, week_day,
        slot.get("weeks"), slot.get("session_type")
    ))
    time_slot_id = cursor.fetchone()[0]

    cursor.execute("""
        INSERT OR IGNORE INTO course_time_mappings (provided_id, time_slot_id)
        VALUES (?, ?)
    """, (provided_id, time_slot_id))
    conn.commit()

def split_instructor_names(raw):
    if not raw:
        return ["Unknown"]
    return [name.strip() for name in re.split(r",|;", raw) if name.strip()]

# === Insert schedule data ===
for program_name, program_data in schedule_data.items():
    program_id = get_program_id(program_name)
    if not program_id:
        print(f"[SKIPPED] Program '{program_name}' not found.")
        continue

    courses_by_semester = program_data.get("courses_by_semester", {})
    for semester_str, courses in courses_by_semester.items():
        semester = int(semester_str)

        for course in courses:
            title = course.get("course")
            extra_info = course.get("extra_info")
            schedule = course.get("schedule", {})

            for group_name, group_data in schedule.items():
                instructor_names = split_instructor_names(group_data.get("instructor", "Unknown"))
                slots = group_data.get("slots", [])

                if not slots:
                    print(f"[WARNING] No slots for course '{title}', group '{group_name}'")

                course_id = get_course_id_by_title(title)
                raw_course_name = title

                provided_id = insert_course_provided(
                    course_id, raw_course_name, program_id,
                    semester, group_name, extra_info
                )

                insert_instructors_for_course(provided_id, instructor_names)
                for slot in slots:
                    insert_slot_and_map(provided_id, slot)

conn.commit()
conn.close()
print("All data inserted successfully.")
