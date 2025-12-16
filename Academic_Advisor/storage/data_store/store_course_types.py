import sqlite3
import json

# --- Static course types ---
STATIC_PROGRAM_COURSE_TYPES = {
    "Programme Génie Informatique et Communications": [
        {"course_type": "UE Obligatoires", "total_credits": 106},
        {"course_type": "UE Obligatoires pour l’option", "total_credits": 44},
        {"course_type": "Optionnelles Fermées", "total_credits": 26},
        {"course_type": "Optionnels Ouvertes", "total_credits": 4},
    ]
}

# --- Utility functions ---
def ensure_course_type_column(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    if "course_type" not in columns:
        print(f"Adding column 'course_type' to {table_name} table...")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN course_type TEXT")
        print("Column added.")
    else:
        print(f"'course_type' column already exists in {table_name}.")

def ensure_program_course_types_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS program_course_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            course_type TEXT NOT NULL,
            total_credits INTEGER NOT NULL,
            FOREIGN KEY (program_id) REFERENCES programs(id)
        )
    """)

def extract_courses(section):
    course_type = section.get("course_type")
    courses = []
    if "courses" in section:
        for c in section["courses"]:
            if "title" in c:
                courses.append((c["title"].strip(), course_type))
    elif "options" in section:
        for option in section["options"]:
            for c in option.get("courses", []):
                if "title" in c:
                    courses.append((c["title"].strip(), course_type))
    return courses

# --- Populate static course types ---
def populate_program_course_types(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    ensure_program_course_types_table(cursor)

    for program_name, course_types in STATIC_PROGRAM_COURSE_TYPES.items():
        cursor.execute("SELECT id FROM programs WHERE name = ?", (program_name,))
        prog_row = cursor.fetchone()
        if not prog_row:
            print(f"[ERROR] Program '{program_name}' not found in database.")
            continue
        program_id = prog_row[0]
        print(f"Populating static course types for program: {program_name} (ID: {program_id})")

        cursor.execute("DELETE FROM program_course_types WHERE program_id = ?", (program_id,))
        for ct in course_types:
            cursor.execute("""
                INSERT INTO program_course_types (program_id, course_type, total_credits)
                VALUES (?, ?, ?)
            """, (program_id, ct["course_type"], ct["total_credits"]))

        print(f"Static course types updated for '{program_name}'.")

    conn.commit()
    conn.close()
    print("All static programs processed successfully.")

# --- Update from JSON ---
def update_course_types_from_json(db_path, json_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure course_type columns exist
    ensure_course_type_column(cursor, "courses")
    ensure_course_type_column(cursor, "courses_provided")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON root must be a list of programs.")

    for program in data:
        program_name = program.get("program")
        sections = program.get("sections")
        if not program_name or not sections:
            print("[WARNING] Program missing 'program' name or 'sections', skipping")
            continue

        cursor.execute("SELECT id FROM programs WHERE name = ?", (program_name,))
        prog_row = cursor.fetchone()
        if not prog_row:
            print(f"[ERROR] Program '{program_name}' not found in database.")
            continue
        program_id = prog_row[0]

        print(f"Updating course types from JSON for program: {program_name} (ID: {program_id})")

        # Clear old course_type info for this program
        cursor.execute("DELETE FROM program_course_types WHERE program_id = ?", (program_id,))
        cursor.execute("UPDATE courses_provided SET course_type = NULL WHERE program_id = ?", (program_id,))

        for section in sections:
            course_type_name = section.get("course_type")
            total_credits = section.get("total_credits")
            if not course_type_name or total_credits is None:
                print(f"[WARNING] Section missing course_type or total_credits, skipping")
                continue

            cursor.execute("""
                INSERT INTO program_course_types (program_id, course_type, total_credits)
                VALUES (?, ?, ?)
            """, (program_id, course_type_name, total_credits))

            for title, ctype in extract_courses(section):
                cursor.execute("""
                    UPDATE courses SET course_type = ? WHERE title = ? COLLATE NOCASE
                """, (ctype, title))
                cursor.execute("""
                    UPDATE courses_provided SET course_type = ?
                    WHERE raw_course_name = ? COLLATE NOCASE AND program_id = ?
                """, (ctype, title, program_id))

        print(f"Updated course types for '{program_name}' from JSON.")

    conn.commit()
    conn.close()
    print("All JSON programs processed successfully.")

# --- Main execution ---
if __name__ == "__main__":
    DB_PATH = "storage/data_store/advising.db"
    JSON_PATH = "storage/data/extracted_courses.json"
    update_course_types_from_json(DB_PATH, JSON_PATH)
    populate_program_course_types(DB_PATH)

