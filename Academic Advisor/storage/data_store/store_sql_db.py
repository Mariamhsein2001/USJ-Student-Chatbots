import sqlite3
import json
from collections import defaultdict

departments = [
    "Département des Classes Préparatoires",
    "Département Génie Électrique et Mécanique",
    "Département Génie Civil et Environnement",
    "Département Génie Chimique et Pétrochimique",
    "Département des Etudes Doctorales"
]

conn = sqlite3.connect("storage/data_store/advising.db")
cursor = conn.cursor()

# === 1. Drop and recreate departments table ===
cursor.executescript("""
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
""")

for name in departments:
    cursor.execute("INSERT OR IGNORE INTO departments (name) VALUES (?)", (name,))

conn.commit()

# === 2. Drop and recreate programs table ===
cursor.executescript("""
DROP TABLE IF EXISTS programs;

CREATE TABLE programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY(department_id) REFERENCES departments(id),
    UNIQUE(department_id, name)
);
""")

programs_by_dept = {
    "Département des Classes Préparatoires": [
        "Programme Préparatoire Génie Chimique et Pétrochimique",
        "Programme Préparatoire Génie Civil",
        "Programme Préparatoire Génie Électrique",
        "Programme Préparatoire Génie Informatique et Communications",
        "Programme Préparatoire Génie Mécanique",
        "Programme Concours Génie Chimique et Pétrochimique",
        "Programme Concours Génie Civil",
        "Programme Concours Génie Électrique",
        "Programme Concours Génie Informatique et Communications",
        "Programme Concours Génie Mécanique"
    ],
    "Département Génie Électrique et Mécanique": [
        "Programme Génie Électrique",
        "Programme Génie Informatique et Communications",
        "Programme Génie Mécanique"
    ],
    "Département Génie Civil et Environnement": [
        "Programme de Génie Civil"
    ],
    "Département Génie Chimique et Pétrochimique": [
        "Programme de Génie Chimique et Pétrochimique"
    ],
    "Département des Etudes Doctorales": [
        "Master en Data Sciences",
        "Master in Artificial Intelligence",
        "Master en Energies Renouvelables",
        "Master en Génie Electrique",
        "Master Oil and Gas: Exploration, Production & Management",
        "Master Structure et Mécanique des Sols",
        "Master en Management de la Sécurité Routière",
        "Master Sciences de l’Eau",
        "Master Télécommunications, Réseaux et Sécurité"
    ]
}

for dept_name, programs in programs_by_dept.items():
    cursor.execute("SELECT id FROM departments WHERE name = ?", (dept_name,))
    dept_id = cursor.fetchone()[0]
    for program in programs:
        cursor.execute("INSERT OR IGNORE INTO programs (department_id, name) VALUES (?, ?)", (dept_id, program))

conn.commit()

# === 3. Drop and recreate courses table WITHOUT program_id ===
cursor.executescript("""
DROP TABLE IF EXISTS courses;

CREATE TABLE courses (
    course_id TEXT PRIMARY KEY,
    title TEXT,
    credits INTEGER,
    description TEXT,
    prerequisites TEXT
);
""")

# === 4. Create program_courses linking table ===
cursor.executescript("""
DROP TABLE IF EXISTS program_courses;

CREATE TABLE program_courses (
    program_id INTEGER NOT NULL,
    course_id TEXT NOT NULL,
    PRIMARY KEY (program_id, course_id),
    FOREIGN KEY(program_id) REFERENCES programs(id),
    FOREIGN KEY(course_id) REFERENCES courses(course_id)
);
""")

def normalize_prerequisites(p):
    if not p or str(p).strip().lower() in ["rien", "none", "null"]:
        return None
    return p.strip()

# Fetch programs to map by department
cursor.execute("""
SELECT programs.id, programs.name, departments.name 
FROM programs JOIN departments ON programs.department_id = departments.id
""")
program_rows = cursor.fetchall()
programs_by_dept = defaultdict(list)
for prog_id, prog_name, dept_name in program_rows:
    programs_by_dept[dept_name].append((prog_id, prog_name))

# === 5. Load courses and insert, link properly ===
with open('data/courses_by_department_summarized.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for dept_name, content in data.items():
    if dept_name == "Département des Etudes Doctorales":
        print(f"Processing doctoral department: {dept_name}")
        for program_name, program_data in content.items():
            prog_id = next((pid for pid, pname in programs_by_dept[dept_name] if pname == program_name), None)
            if not prog_id:
                print(f"[SKIPPED] Program '{program_name}' not found in DB.")
                continue
            course_count = 0
            for course in program_data.get("courses", []):
                code = course.get("code")
                if not code:
                    print(f"[WARNING] Skipping course with missing course_id in program '{program_name}'")
                    continue
                cursor.execute("""
                    INSERT OR IGNORE INTO courses (course_id, title, credits, description, prerequisites)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    code,
                    course.get("title"),
                    course.get("credits"),
                    course.get("description"),
                    normalize_prerequisites(course.get("prerequisites"))
                ))
                cursor.execute("""
                    INSERT OR IGNORE INTO program_courses (program_id, course_id)
                    VALUES (?, ?)
                """, (prog_id, code))
                course_count += 1
            print(f"Inserted and linked {course_count} courses for program '{program_name}'")
    else:
        print(f"Processing department: {dept_name}")
        course_count = 0
        for course in content:
            code = course.get("code")
            if not code:
                print(f"[WARNING] Skipping course with missing course_id in department '{dept_name}'")
                continue
            cursor.execute("""
                INSERT OR IGNORE INTO courses (course_id, title, credits, description, prerequisites)
                VALUES (?, ?, ?, ?, ?)
            """, (
                code,
                course.get("title"),
                course.get("credits"),
                course.get("description"),
                normalize_prerequisites(course.get("prerequisites"))
            ))
            for prog_id, _ in programs_by_dept[dept_name]:
                cursor.execute("""
                    INSERT OR IGNORE INTO program_courses (program_id, course_id)
                    VALUES (?, ?)
                """, (prog_id, code))
            course_count += 1
        print(f"Inserted and linked {course_count} courses for department '{dept_name}'")

conn.commit()

# === 6. Summary counts ===
cursor.execute("SELECT COUNT(*) FROM courses")
total_courses = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM programs")
total_programs = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM program_courses")
total_links = cursor.fetchone()[0]

print(f"\nSummary:")
print(f"Total courses: {total_courses}")
print(f"Total programs: {total_programs}")
print(f"Total program-course links: {total_links}\n")

# Optional: print counts per department and program
for dept_name in programs_by_dept.keys():
    cursor.execute("""
        SELECT COUNT(pc.course_id)
        FROM program_courses pc
        JOIN programs p ON pc.program_id = p.id
        JOIN departments d ON p.department_id = d.id
        WHERE d.name = ?
    """, (dept_name,))
    dept_course_count = cursor.fetchone()[0]
    print(f"Department '{dept_name}' has {dept_course_count} courses linked.")

    for prog_id, prog_name in programs_by_dept[dept_name]:
        cursor.execute("""
            SELECT COUNT(course_id)
            FROM program_courses
            WHERE program_id = ?
        """, (prog_id,))
        prog_course_count = cursor.fetchone()[0]
        print(f"  Program '{prog_name}' has {prog_course_count} courses linked.")

conn.close()
print("Database setup and insertion complete.")
