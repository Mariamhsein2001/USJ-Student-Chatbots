
import sqlite3

conn = sqlite3.connect("storage/data_store/advising.db")
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in DB:", tables)

# For example, print first 5 rows of departments
cursor.execute("SELECT * FROM departments LIMIT 5;")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()
