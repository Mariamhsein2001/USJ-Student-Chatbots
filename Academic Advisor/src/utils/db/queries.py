# utils/db/queries.py

# --- User info ---
GET_USER_INFO = """
    SELECT u.user_id, u.username, ui.current_semester, ui.gpa,
           d.name as department, p.name as program, ui.track, p.id as program_id
    FROM users u
    JOIN user_info ui ON u.user_id = ui.user_id
    JOIN departments d ON ui.department_id = d.id
    JOIN programs p ON ui.program_id = p.id
    WHERE u.username = ? AND ui.status = 'current'
"""

GET_USER_INFO_ROWS = """
    SELECT id, status FROM user_info
    WHERE user_id = ?
"""


# --- User courses ---
GET_USER_COURSES = """
    SELECT DISTINCT uc.course_id, ui.status, uc.grade
    FROM user_courses uc
    JOIN user_info ui ON uc.user_info_id = ui.id
    WHERE uc.user_info_id IN ({placeholders})
      AND (ui.status != 'current' OR uc.grade >= 10)
"""

GET_COURSES_WITH_STATUS = """
    SELECT 
        apc.course_code,
        apc.course_title,
        upc.grade,
        upc.status,
        upc.failed
    FROM user_plan_courses AS upc
    JOIN academic_plan_courses AS apc ON upc.plan_course_id = apc.id
    JOIN users AS u ON upc.user_id = u.user_id
    WHERE u.username = ?
      AND upc.status IN ('passed', 'failed')
"""

# --- Courses by program & semester ---
GET_COURSES_BY_PROGRAM_SEMESTER = """
    SELECT cp.id, cp.raw_course_name, cp.group_name, cp.course_type, cp.extra_info,
           c.course_id, c.title, c.credits, c.prerequisites,
           i.name, ts.start_time, ts.end_time, ts.week_day, ts.weeks, ts.session_type
    FROM courses_provided cp
    LEFT JOIN courses c ON cp.course_id = c.course_id
    LEFT JOIN instructors_courses_provided icp ON cp.id = icp.provided_id
    LEFT JOIN instructors i ON icp.instructor_id = i.id
    LEFT JOIN course_time_mappings ctm ON cp.id = ctm.provided_id
    LEFT JOIN time_slots ts ON ctm.time_slot_id = ts.id
    JOIN programs p ON cp.program_id = p.id
    WHERE p.name LIKE ? AND cp.semester = ?
    ORDER BY cp.raw_course_name, cp.group_name, ts.week_day, ts.start_time
"""

# --- Individual course info ---
GET_COURSE_DESCRIPTION = "SELECT description FROM courses WHERE course_id = ?"
GET_COURSE_BY_CODE = "SELECT course_type, credits FROM courses WHERE course_id = ?"

# --- Program course types ---
GET_PROGRAM_COURSE_TYPES = """
    SELECT course_type, total_credits
    FROM program_course_types
    WHERE program_id = ?
"""

# --- User authentication ---
CHECK_USER_CREDENTIALS = "SELECT password FROM users WHERE username = ?"

# --- Credit queries ---
GET_USER_TOTAL_CREDITS_BY_TYPE_WITH_TRACK = """
    SELECT c.course_type, SUM(c.credits)
    FROM user_courses uc
    JOIN user_info ui ON uc.user_info_id = ui.id
    JOIN users u ON ui.user_id = u.user_id
    JOIN courses c ON uc.course_id = c.course_id
    WHERE u.username = ? AND ui.status = 'current' AND uc.grade >= 10
    GROUP BY c.course_type
"""

GET_CREDIT_EXPECTED = """
    SELECT pct.course_type, pct.total_credits
        FROM users u
        JOIN user_info ui ON u.user_id = ui.user_id
        JOIN program_course_types pct ON pct.program_id = ui.program_id
        WHERE u.username = ? AND ui.status = 'current'
        """