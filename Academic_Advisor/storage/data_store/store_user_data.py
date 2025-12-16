import sqlite3
import json

# Connect to the SQLite database
conn = sqlite3.connect("storage/data_store/advising.db")
cursor = conn.cursor()

cursor.executescript("""
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS user_info;
DROP TABLE IF EXISTS user_courses;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    department_id INTEGER,
    program_id INTEGER,
    status TEXT,
    current_semester INTEGER,
    gpa REAL,
    enrollment_year INTEGER,
    total_credits_completed INTEGER DEFAULT 0,
    track TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(department_id) REFERENCES departments(id),
    FOREIGN KEY(program_id) REFERENCES programs(id)
);


CREATE TABLE user_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_info_id INTEGER NOT NULL,
    course_id TEXT NOT NULL,
    grade REAL,
    semester_taken INTEGER,
    year_taken INTEGER,
    FOREIGN KEY(user_info_id) REFERENCES user_info(id),
    FOREIGN KEY(course_id) REFERENCES courses(course_id),
    UNIQUE(user_info_id, course_id)
);
""")

conn.commit()

# === Insert users and their info including GPA and course grades ===
with open("data/user_info.json", "r", encoding="utf-8") as f:
    users_data = json.load(f)

for user in users_data:
    username = user["user"]
    password = "defaultpassword"

    # Insert into users table
    cursor.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", (username, password))
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()[0]

    # Loop over each department/program entry
    for info in user["user_info"]:
        dept_name = info["department"]
        prog_name = info["program"]

        cursor.execute("SELECT id FROM departments WHERE name = ?", (dept_name,))
        department_row = cursor.fetchone()
        if not department_row:
            print(f"[WARNING] Department '{dept_name}' not found for user {username}")
            continue
        department_id = department_row[0]

        cursor.execute("SELECT id FROM programs WHERE name LIKE ? AND department_id = ?", (f"%{prog_name}%", department_id))
        program_row = cursor.fetchone()
        if not program_row:
            print(f"[WARNING] Program '{prog_name}' not found for user {username}")
            continue
        program_id = program_row[0]

        # Insert into user_info table
        cursor.execute("""
            INSERT INTO user_info (
                user_id, department_id, program_id, status, current_semester,
                gpa, enrollment_year, total_credits_completed, track
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            department_id,
            program_id,
            info.get("status"),
            info.get("current_semester"),
            info.get("gpa"),
            info.get("enrollment_year"),
            info.get("total_credits"),
            info.get("track")
        ))


        user_info_id = cursor.lastrowid

        # Insert courses for this department
        for course in info.get("courses_taken", []):
            course_code = course.get("code")  # can be None
            grade = course.get("grade")
            year_taken = course.get("year_taken")
            semester_taken = course.get("semester_taken")

            cursor.execute("""
                INSERT OR IGNORE INTO user_courses (user_info_id, course_id, grade, semester_taken, year_taken)
                VALUES (?, ?, ?, ?, ?)
            """, (user_info_id, course_code, grade, semester_taken, year_taken))


conn.commit()
conn.close()
print("Database setup and user insertion complete.")
