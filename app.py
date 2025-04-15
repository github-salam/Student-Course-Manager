from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure random key
DATABASE = 'project.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Create tables and initial data
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            instructor TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS student_course (
            student_id INTEGER,
            course_id INTEGER,
            PRIMARY KEY (student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
    ''')

    cur.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ('admin', 'admin'))

    cur.execute('''
        CREATE TABLE IF NOT EXISTS enrollment_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_id INTEGER,
            enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('DROP TRIGGER IF EXISTS log_enrollment')
    cur.execute('''
        CREATE TRIGGER log_enrollment
        AFTER INSERT ON student_course
        BEGIN
            INSERT INTO enrollment_log (student_id, course_id)
            VALUES (NEW.student_id, NEW.course_id);
        END;
    ''')

    conn.commit()
    conn.close()

# Authentication decorator
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    return redirect(url_for('home'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        c = conn.cursor()
        username = request.form['username']
        password = request.form['password']
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user'] = username
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    conn = get_db_connection()
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
@login_required
def delete_student(student_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return redirect('/students')

@app.route('/courses', methods=['GET', 'POST'])
@login_required
def courses():
    conn = get_db_connection()
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
@login_required
def delete_course(course_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()
    return redirect('/courses')

@app.route('/assign', methods=['GET', 'POST'])
@login_required
def assign_students():
    conn = get_db_connection()
    c = conn.cursor()
    message = None

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')

        if not student_id or not course_id:
            message = "⚠️ Both student and course must be selected."
        else:
            c.execute('''
                INSERT INTO student_course (student_id, course_id)
                SELECT ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM student_course WHERE student_id = ? AND course_id = ?
                )
            ''', (student_id, course_id, student_id, course_id))
            conn.commit()

            if c.rowcount > 0:
                message = "✅ Student successfully assigned to the course!"
            else:
                message = "⚠️ This student is already assigned to this course."

    c.execute('SELECT id, name FROM students')
    students = c.fetchall()
    c.execute('SELECT id, name FROM courses')
    courses = c.fetchall()

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
@login_required
def view_enrollments():
    conn = get_db_connection()
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
@login_required
def delete_enrollment(student_id, course_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM student_course WHERE student_id=? AND course_id=?", (student_id, course_id))
    conn.commit()
    conn.close()
    return redirect('/enrollments')

@app.route('/enroll', methods=['GET', 'POST'])
@login_required
def enroll():
    conn = get_db_connection()
    c = conn.cursor()
    message = None

    if request.method == 'POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        c.execute('''
            INSERT INTO student_course (student_id, course_id)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM student_course WHERE student_id = ? AND course_id = ?
            )
        ''', (student_id, course_id, student_id, course_id))
        conn.commit()
        message = "✅ Enrollment successful!"

    c.execute("SELECT id, name FROM students")
    students = c.fetchall()
    c.execute("SELECT id, name FROM courses")
    courses = c.fetchall()
    c.execute('''
        SELECT sc.student_id, sc.course_id, s.name, c.name 
        FROM student_course sc
        JOIN students s ON sc.student_id = s.id
        JOIN courses c ON sc.course_id = c.id
    ''')
    enrollments = c.fetchall()

    conn.close()
    return render_template('enroll.html', students=students, courses=courses, enrollments=enrollments, message=message)

@app.route('/enroll/delete/<int:student_id>/<int:course_id>')
@login_required
def delete_enroll(student_id, course_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM student_course WHERE student_id = ? AND course_id = ?", (student_id, course_id))
    conn.commit()
    conn.close()
    return redirect('/enroll')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    total_students = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_courses = cur.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    total_enrollments = cur.execute("SELECT COUNT(*) FROM student_course").fetchone()[0]

    cur.execute('''
        SELECT courses.name, COUNT(*) AS enroll_count
        FROM student_course
        JOIN courses ON student_course.course_id = courses.id
        GROUP BY courses.name
        ORDER BY enroll_count DESC
        LIMIT 1
    ''')
    most_popular = cur.fetchone()

    cur.execute('''
        SELECT * FROM students
        WHERE id NOT IN (
            SELECT student_id FROM student_course
        )
    ''')
    unenrolled_students = cur.fetchall()

    cur.execute("SELECT * FROM student_course_view")
    enrollments_view = cur.fetchall()

    cur.execute("SELECT * FROM student_insert_log ORDER BY inserted_at DESC LIMIT 5")
    student_logs = cur.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        total_students=total_students,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        most_popular=most_popular,
        unenrolled_students=unenrolled_students,
        enrollments_view=enrollments_view,
        student_logs=student_logs
    )

def initialize_advanced_sql():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE VIEW IF NOT EXISTS student_course_view AS
            SELECT s.id AS student_id, s.name AS student_name, COUNT(sc.course_id) AS course_count
            FROM students s
            LEFT JOIN student_course sc ON s.id = sc.student_id
            GROUP BY s.id
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS student_insert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                name TEXT,
                email TEXT,
                inserted_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('DROP TRIGGER IF EXISTS log_student_insert')

        conn.execute('''
            CREATE TRIGGER log_student_insert
            AFTER INSERT ON students
            BEGIN
                INSERT INTO student_insert_log (student_id, name, email)
                VALUES (NEW.id, NEW.name, NEW.email);
            END;
        ''')

if __name__ == '__main__':
    init_db()
    initialize_advanced_sql()
    app.run(debug=True)
