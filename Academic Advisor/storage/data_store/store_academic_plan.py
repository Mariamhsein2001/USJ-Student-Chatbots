import sqlite3
import json

DB_PATH = "storage/data_store/advising.db"
PLAN_PATH = "storage/data/proposed_plan.json"
USER_DATA_PATH = "storage/data/user_info.json"

def create_tables(cursor):
    # Drop tables if they exist (drop dependent tables first)
    cursor.execute("DROP TABLE IF EXISTS user_plan_courses;")
    cursor.execute("DROP TABLE IF EXISTS academic_plan_courses;")
    cursor.execute("DROP TABLE IF EXISTS academic_plans;")

    # Create academic_plans table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS academic_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id INTEGER NOT NULL,
        academic_year INTEGER NOT NULL,
        UNIQUE(program_id, academic_year),
        FOREIGN KEY(program_id) REFERENCES programs(id)
    );
    """)

    # Create academic_plan_courses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS academic_plan_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        course_code TEXT,
        course_title TEXT NOT NULL,
        credits INTEGER NOT NULL,
        semester INTEGER NOT NULL,
        FOREIGN KEY(plan_id) REFERENCES academic_plans(id)
    );
    """)

    # Create user_plan_courses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_plan_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_course_id INTEGER NOT NULL,
        grade REAL,
        status TEXT,
        failed INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(plan_course_id) REFERENCES academic_plan_courses(id),
        UNIQUE(user_id, plan_course_id)
    );
    """)

def insert_academic_plan(conn, plan_data):
    cursor = conn.cursor()
    program_name = plan_data["program"]
    year = plan_data["year"]

    # Get program ID
    cursor.execute("SELECT id FROM programs WHERE name = ?", (program_name,))
    res = cursor.fetchone()
    if not res:
        raise ValueError(f"Program '{program_name}' not found in the database.")
    program_id = res[0]

    # Insert the academic plan
    try:
        cursor.execute("""
            INSERT INTO academic_plans (program_id, academic_year)
            VALUES (?, ?)
        """, (program_id, year))
        plan_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        print(f"Plan for program '{program_name}' and year {year} already exists. Skipping insertion.")
        return

    # Insert all courses
    for semester_info in plan_data["plan"]:
        semester = semester_info["semester"]
        for course in semester_info["courses"]:
            # Insert group titles (like "Optionnelles fermées", etc.)
            if "options" in course:
                for subcourse in course["options"]:
                    cursor.execute("""
                        INSERT INTO academic_plan_courses (plan_id, course_code, course_title, credits, semester)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        plan_id,
                        subcourse.get("code"),
                        subcourse["title"],
                        subcourse["credits"],
                        semester
                    ))
            else:
                cursor.execute("""
                    INSERT INTO academic_plan_courses (plan_id, course_code, course_title, credits, semester)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    plan_id,
                    course.get("code"),
                    course["title"],
                    course["credits"],
                    semester
                ))

    conn.commit()
    print(f"Inserted academic plan for '{program_name}', year {year}")

def insert_users_and_grades(conn, users_data):
    cursor = conn.cursor()

    for user_entry in users_data:
        username = user_entry["user"]

        # Get user_id
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            print(f"[WARN] User '{username}' not found. Skipping.")
            continue
        user_id = user_row[0]

        # Verify user info exists in DB
        cursor.execute("SELECT user_id FROM user_info WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            print(f"[WARN] User info not found for '{username}'. Skipping.")
            continue

        # Iterate through all program entries in user_info
        for program_info in user_entry["user_info"]:
            courses_taken = program_info.get("courses_taken", [])

            # Fetch program and enrollment year
            program = program_info.get("program")
            year = program_info.get("enrollment_year")

            if not program or year is None:
                print(f"[WARN] Missing program/year for '{username}'. Skipping entry.")
                continue

            # Get academic plan ID
            cursor.execute("""
                SELECT id FROM academic_plans
                WHERE program_id = (SELECT id FROM programs WHERE name LIKE ?)
                AND academic_year = ?
            """, (f"%{program}%", year))
            plan_row = cursor.fetchone()
            if not plan_row:
                print(f"[WARN] Academic plan not found for program '{program}' year {year}. Skipping.")
                continue
            plan_id = plan_row[0]

            # Get plan courses
            cursor.execute("""
                SELECT id, course_code, course_title
                FROM academic_plan_courses
                WHERE plan_id = ?
            """, (plan_id,))
            plan_courses = cursor.fetchall()

            # Map course codes and titles to IDs
            code_to_id = {row[1]: row[0] for row in plan_courses if row[1]}
            title_to_id = {row[2]: row[0] for row in plan_courses}

            # Map taken courses for lookup
            taken_courses_map = {}
            for c in courses_taken:
                if c.get("code"):
                    taken_courses_map[c["code"]] = c
                if c.get("title"):
                    taken_courses_map[c["title"]] = c

            # Insert or update user plan courses
            for plan_course_id, code, title in plan_courses:
                course_info = taken_courses_map.get(code) or taken_courses_map.get(title)

                if course_info:
                    grade = course_info.get("grade")
                    if grade is None:
                        status, failed = "pending", 0
                    elif grade >= 10:
                        status, failed = "passed", 0
                    else:
                        status, failed = "failed", 1

                    cursor.execute("""
                        INSERT INTO user_plan_courses (user_id, plan_course_id, grade, status, failed)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(user_id, plan_course_id) DO UPDATE SET
                            grade=excluded.grade,
                            status=excluded.status,
                            failed=excluded.failed
                    """, (user_id, plan_course_id, grade, status, failed))
                else:
                    cursor.execute("""
                        INSERT OR IGNORE INTO user_plan_courses (user_id, plan_course_id, grade, status, failed)
                        VALUES (?, ?, NULL, 'pending', 0)
                    """, (user_id, plan_course_id))

    conn.commit()
    print("Inserted/updated user plan courses data.")

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    create_tables(cursor)

    # Insert academic plans (multiple programs)
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    # Loop through each plan in the list
    for plan in plan_data:
        insert_academic_plan(conn, plan)

    # Insert user data
    with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
        users_data = json.load(f)
    insert_users_and_grades(conn, users_data)

    conn.close()

if __name__ == "__main__":
    main()
