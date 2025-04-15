import sqlite3

conn = sqlite3.connect('database/project.db')
cursor = conn.cursor()

# Check students
cursor.execute('SELECT * FROM students')
print(cursor.fetchall())

# Check courses
cursor.execute('SELECT * FROM courses')
print(cursor.fetchall())

conn.close()
