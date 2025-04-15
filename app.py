from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)

# Initialize the database with both students and courses tables
def init_db():
    if not os.path.exists('project.db'):
        conn = sqlite3.connect('project.db')
        c = conn.cursor()

        # Students table
        c.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            )
        ''')

        # Courses table
        c.execute('''
            CREATE TABLE courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                instructor TEXT NOT NULL
            )
        ''')

        # student course table
        c.execute('''
        CREATE TABLE IF NOT EXISTS student_course (
            student_id INTEGER,
            course_id INTEGER,
            PRIMARY KEY (student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );
        ''')

        conn.commit()
        conn.close()

# Home route
@app.route('/')
def home():
    return render_template('home.html')

# Students route
@app.route('/students', methods=['GET', 'POST'])
def students():
    conn = sqlite3.connect('project.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        c.execute("INSERT INTO students (name, email) VALUES (?, ?)", (name, email))
        conn.commit()

    c.execute("SELECT * FROM students")
    students = c.fetchall()
    conn.close()
    return render_template('students.html', students=students)

@app.route('/students/delete/<int:student_id>')
def delete_student(student_id):
    conn = sqlite3.connect('project.db')
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return redirect('/students')

# Courses route
@app.route('/courses', methods=['GET', 'POST'])
def courses():
    conn = sqlite3.connect('project.db')
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        instructor = request.form['instructor']
        c.execute("INSERT INTO courses (name, instructor) VALUES (?, ?)", (name, instructor))
        conn.commit()

    c.execute("SELECT * FROM courses")
    courses = c.fetchall()
    conn.close()
    return render_template('courses.html', courses=courses)

@app.route('/courses/delete/<int:course_id>')
def delete_course(course_id):
    conn = sqlite3.connect('project.db')
    c = conn.cursor()
    c.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()
    return redirect('/courses')


@app.route('/assign', methods=['GET', 'POST'])
def assign_students():
    conn = sqlite3.connect('project.db')
    c = conn.cursor()
    message = None

    if request.method == 'POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']

        # Prevent duplicate assignment
        c.execute('''
            INSERT INTO student_course (student_id, course_id)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM student_course WHERE student_id = ? AND course_id = ?
            )
        ''', (student_id, course_id, student_id, course_id))
        conn.commit()
        message = "✅ Student successfully assigned to the course!"

    # Get dropdown options
    c.execute('SELECT id, name FROM students')
    students = c.fetchall()
    c.execute('SELECT id, name FROM courses')
    courses = c.fetchall()

    # Get current enrollments (without rowid)
    c.execute('''
        SELECT sc.student_id, s.name, c.name
        FROM student_course sc
        JOIN students s ON sc.student_id = s.id
        JOIN courses c ON sc.course_id = c.id
    ''')
    enrollments = c.fetchall()

    conn.close()
    return render_template('assign.html', students=students, courses=courses, enrollments=enrollments, message=message)


@app.route('/enrollments')
def view_enrollments():
    conn = sqlite3.connect('project.db')
    c = conn.cursor()
    c.execute('''
        SELECT s.name AS student_name, c.name AS course_name 
        FROM student_course sc
        JOIN students s ON sc.student_id = s.id
        JOIN courses c ON sc.course_id = c.id
    ''')
    enrollments = c.fetchall()
    conn.close()
    return render_template('enrollments.html', enrollments=enrollments)

@app.route('/enrollments/delete/<int:student_id>/<int:course_id>')
def delete_enrollment(student_id, course_id):
    conn = sqlite3.connect('project.db')
    c = conn.cursor()
    c.execute("DELETE FROM student_course WHERE student_id=? AND course_id=?", (student_id, course_id))
    conn.commit()
    conn.close()
    return redirect('/enrollments')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
