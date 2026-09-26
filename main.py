"""
Student Management System
--------------------------
A console-based Student Management System with:
  - Add / Edit / Delete / View students
  - Grades management (add, update, view per subject)
  - Attendance tracking (mark present/absent, view history & percentage)
  - Search (by name, ID, or class)

Data is persisted locally in an SQLite database file: school.db
Run with: python student_management_system.py
"""

import sqlite3
import os
from datetime import date

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "school.db")


# ----------------------------------------------------------------------
# Database layer
# ----------------------------------------------------------------------
class Database:
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT UNIQUE,
                class_name TEXT,
                email TEXT,
                phone TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                marks REAL NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status TEXT CHECK(status IN ('Present', 'Absent')) NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                UNIQUE(student_id, date)
            )
        """)
        self.conn.commit()

    def close(self):
        self.conn.close()


# ----------------------------------------------------------------------
# Student Management System
# ----------------------------------------------------------------------
class StudentManagementSystem:
    def __init__(self):
        self.db = Database()
        self.conn = self.db.conn

    # ---------------- Student CRUD ----------------
    def add_student(self, name, roll_no, class_name, email="", phone=""):
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO students (name, roll_no, class_name, email, phone) VALUES (?, ?, ?, ?, ?)",
                (name, roll_no, class_name, email, phone),
            )
            self.conn.commit()
            print(f"Student '{name}' added with ID {cur.lastrowid}.")
        except sqlite3.IntegrityError:
            print(f"Error: roll number '{roll_no}' already exists.")

    def edit_student(self, student_id, **fields):
        if not fields:
            print("Nothing to update.")
            return
        if not self._student_exists(student_id):
            print("Student not found.")
            return
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [student_id]
        cur = self.conn.cursor()
        try:
            cur.execute(f"UPDATE students SET {columns} WHERE id = ?", values)
            self.conn.commit()
            print("Student updated successfully.")
        except sqlite3.IntegrityError:
            print("Error: roll number must be unique.")

    def delete_student(self, student_id):
        if not self._student_exists(student_id):
            print("Student not found.")
            return
        cur = self.conn.cursor()
        cur.execute("DELETE FROM students WHERE id = ?", (student_id,))
        self.conn.commit()
        print("Student deleted (along with grades & attendance records).")

    def view_all_students(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, roll_no, class_name, email, phone FROM students ORDER BY id")
        rows = cur.fetchall()
        self._print_students(rows)

    def view_student(self, student_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, roll_no, class_name, email, phone FROM students WHERE id = ?", (student_id,))
        row = cur.fetchone()
        if not row:
            print("Student not found.")
            return
        self._print_students([row])
        self._show_grades(student_id)
        self._show_attendance_summary(student_id)

    def _student_exists(self, student_id):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM students WHERE id = ?", (student_id,))
        return cur.fetchone() is not None

    @staticmethod
    def _print_students(rows):
        if not rows:
            print("No students found.")
            return
        print(f"\n{'ID':<5}{'Name':<20}{'Roll No':<12}{'Class':<10}{'Email':<25}{'Phone':<15}")
        print("-" * 87)
        for r in rows:
            print(f"{r[0]:<5}{r[1]:<20}{r[2] or '':<12}{r[3] or '':<10}{r[4] or '':<25}{r[5] or '':<15}")
        print()

    # ---------------- Grades ----------------
    def add_grade(self, student_id, subject, marks):
        if not self._student_exists(student_id):
            print("Student not found.")
            return
        cur = self.conn.cursor()
        cur.execute("INSERT INTO grades (student_id, subject, marks) VALUES (?, ?, ?)", (student_id, subject, marks))
        self.conn.commit()
        print(f"Grade added: {subject} = {marks}")

    def update_grade(self, grade_id, marks):
        cur = self.conn.cursor()
        cur.execute("UPDATE grades SET marks = ? WHERE id = ?", (marks, grade_id))
        self.conn.commit()
        if cur.rowcount:
            print("Grade updated.")
        else:
            print("Grade record not found.")

    def _show_grades(self, student_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id, subject, marks FROM grades WHERE student_id = ?", (student_id,))
        rows = cur.fetchall()
        print("Grades:")
        if not rows:
            print("  No grades recorded.")
            return
        for gid, subject, marks in rows:
            print(f"  [GradeID {gid}] {subject}: {marks}")
        avg = sum(r[2] for r in rows) / len(rows)
        print(f"  Average: {avg:.2f}")

    # ---------------- Attendance ----------------
    def mark_attendance(self, student_id, status, att_date=None):
        if not self._student_exists(student_id):
            print("Student not found.")
            return
        att_date = att_date or date.today().isoformat()
        status = status.capitalize()
        if status not in ("Present", "Absent"):
            print("Status must be 'Present' or 'Absent'.")
            return
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                (student_id, att_date, status),
            )
            self.conn.commit()
            print(f"Attendance marked: {att_date} - {status}")
        except sqlite3.IntegrityError:
            cur.execute(
                "UPDATE attendance SET status = ? WHERE student_id = ? AND date = ?",
                (status, student_id, att_date),
            )
            self.conn.commit()
            print(f"Attendance updated: {att_date} - {status}")

    def _show_attendance_summary(self, student_id):
        cur = self.conn.cursor()
        cur.execute("SELECT date, status FROM attendance WHERE student_id = ? ORDER BY date", (student_id,))
        rows = cur.fetchall()
        print("Attendance:")
        if not rows:
            print("  No attendance recorded.")
            return
        present = sum(1 for r in rows if r[1] == "Present")
        total = len(rows)
        for d, status in rows:
            print(f"  {d}: {status}")
        print(f"  Attendance %: {present / total * 100:.1f}% ({present}/{total} days present)")

    # ---------------- Search ----------------
    def search_students(self, keyword):
        cur = self.conn.cursor()
        like = f"%{keyword}%"
        cur.execute(
            """SELECT id, name, roll_no, class_name, email, phone FROM students
               WHERE name LIKE ? OR roll_no LIKE ? OR class_name LIKE ? OR CAST(id AS TEXT) = ?""",
            (like, like, like, keyword),
        )
        rows = cur.fetchall()
        self._print_students(rows)


# ----------------------------------------------------------------------
# Console Menu
# ----------------------------------------------------------------------
def input_int(prompt):
    while True:
        val = input(prompt).strip()
        try:
            return int(val)
        except ValueError:
            print("Please enter a valid number.")


def main():
    sms = StudentManagementSystem()

    menu = """
========== STUDENT MANAGEMENT SYSTEM ==========
1.  Add Student
2.  Edit Student
3.  Delete Student
4.  View All Students
5.  View Single Student (details, grades, attendance)
6.  Search Students
7.  Add Grade
8.  Update Grade
9.  Mark Attendance
0.  Exit
=================================================
"""

    while True:
        print(menu)
        choice = input("Enter choice: ").strip()

        if choice == "1":
            name = input("Name: ").strip()
            roll_no = input("Roll No: ").strip()
            class_name = input("Class: ").strip()
            email = input("Email (optional): ").strip()
            phone = input("Phone (optional): ").strip()
            sms.add_student(name, roll_no, class_name, email, phone)

        elif choice == "2":
            sid = input_int("Student ID to edit: ")
            print("Leave blank to skip a field.")
            fields = {}
            name = input("New Name: ").strip()
            if name:
                fields["name"] = name
            roll_no = input("New Roll No: ").strip()
            if roll_no:
                fields["roll_no"] = roll_no
            class_name = input("New Class: ").strip()
            if class_name:
                fields["class_name"] = class_name
            email = input("New Email: ").strip()
            if email:
                fields["email"] = email
            phone = input("New Phone: ").strip()
            if phone:
                fields["phone"] = phone
            sms.edit_student(sid, **fields)

        elif choice == "3":
            sid = input_int("Student ID to delete: ")
            confirm = input(f"Confirm delete student {sid}? (y/n): ").strip().lower()
            if confirm == "y":
                sms.delete_student(sid)

        elif choice == "4":
            sms.view_all_students()

        elif choice == "5":
            sid = input_int("Student ID: ")
            sms.view_student(sid)

        elif choice == "6":
            keyword = input("Search by name, roll no, class, or ID: ").strip()
            sms.search_students(keyword)

        elif choice == "7":
            sid = input_int("Student ID: ")
            subject = input("Subject: ").strip()
            marks = float(input("Marks: ").strip())
            sms.add_grade(sid, subject, marks)

        elif choice == "8":
            gid = input_int("Grade ID to update: ")
            marks = float(input("New Marks: ").strip())
            sms.update_grade(gid, marks)

        elif choice == "9":
            sid = input_int("Student ID: ")
            status = input("Status (Present/Absent): ").strip()
            att_date = input("Date (YYYY-MM-DD, blank = today): ").strip() or None
            sms.mark_attendance(sid, status, att_date)

        elif choice == "0":
            print("Goodbye!")
            sms.db.close()
            break

        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main()
