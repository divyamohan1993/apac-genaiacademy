"""
EduPulse - Seed Data Generator
Generates 200 students, 15 subjects, 1500+ enrollments across 4 semesters.
Deterministic via fixed random seed for reproducibility.

Usage:
  python seed_data.py --sql          # Output seed_data.sql file
  python seed_data.py --db           # Insert directly into AlloyDB/PostgreSQL
"""

import argparse
import random
import os
from datetime import date, timedelta

random.seed(42)

DEPARTMENTS = ["Computer Science", "Mathematics", "Physics", "Business"]
SEMESTERS = ["2024-S1", "2024-S2", "2025-S1", "2025-S2"]
GENDERS = ["Male", "Female"]

FIRST_NAMES_M = [
    "Aarav", "Vihaan", "Aditya", "Sai", "Arjun", "Reyansh", "Ayaan", "Krishna",
    "Ishaan", "Shaurya", "Atharva", "Vivaan", "Ansh", "Dhruv", "Kabir",
    "Ritvik", "Aarush", "Kian", "Darsh", "Veer", "Sahil", "Rohan", "Amit",
    "Raj", "Vikram", "Nikhil", "Pranav", "Tanmay", "Harsh", "Dev",
    "Kunal", "Manish", "Rahul", "Suresh", "Akash", "Gaurav", "Naveen",
    "Piyush", "Rishi", "Siddharth", "Tarun", "Uday", "Varun", "Yash",
    "Ajay", "Deepak", "Karthik", "Mohan", "Neeraj", "Om",
]
FIRST_NAMES_F = [
    "Aanya", "Saanvi", "Myra", "Ananya", "Aadhya", "Isha", "Priya", "Diya",
    "Kavya", "Riya", "Meera", "Nisha", "Pooja", "Sneha", "Tanvi",
    "Aditi", "Bhavna", "Chitra", "Divya", "Ekta", "Fatima", "Gauri",
    "Hema", "Ira", "Jaya", "Kiara", "Lakshmi", "Manju", "Neha", "Oviya",
    "Pallavi", "Radhika", "Sakshi", "Tara", "Uma", "Vidya", "Yamini",
    "Zara", "Anjali", "Bhumi", "Charvi", "Dia", "Eva", "Falguni",
    "Gita", "Harini", "Indu", "Juhi", "Komal", "Lata",
]
LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Reddy", "Nair", "Gupta", "Joshi",
    "Verma", "Iyer", "Das", "Rao", "Mehta", "Shah", "Pillai",
    "Chatterjee", "Mukherjee", "Banerjee", "Sen", "Bose", "Ghosh", "Roy",
    "Malhotra", "Kapoor", "Chopra", "Arora", "Bhatt", "Pandey", "Mishra",
    "Tiwari", "Saxena", "Agarwal", "Jain", "Sinha", "Chauhan", "Yadav",
    "Thakur", "Kulkarni", "Deshpande", "Patil",
]

SUBJECTS = [
    ("Data Structures & Algorithms", "Computer Science", 4),
    ("Database Management Systems", "Computer Science", 4),
    ("Machine Learning", "Computer Science", 3),
    ("Operating Systems", "Computer Science", 4),
    ("Linear Algebra", "Mathematics", 3),
    ("Probability & Statistics", "Mathematics", 3),
    ("Calculus III", "Mathematics", 4),
    ("Discrete Mathematics", "Mathematics", 3),
    ("Quantum Mechanics", "Physics", 4),
    ("Electrodynamics", "Physics", 3),
    ("Thermodynamics", "Physics", 3),
    ("Financial Accounting", "Business", 3),
    ("Marketing Management", "Business", 3),
    ("Microeconomics", "Business", 4),
    ("Business Analytics", "Business", 3),
]


def generate_students(n=200):
    students = []
    for i in range(1, n + 1):
        gender = random.choice(GENDERS)
        if gender == "Male":
            first = random.choice(FIRST_NAMES_M)
        else:
            first = random.choice(FIRST_NAMES_F)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        dept = DEPARTMENTS[(i - 1) % len(DEPARTMENTS)]
        year = random.choice([2022, 2023, 2024])
        dob = date(2000 + random.randint(0, 4), random.randint(1, 12), random.randint(1, 28))
        email = f"{first.lower()}.{last.lower()}{i}@edupulse.edu"
        students.append((i, name, email, year, dept, gender, dob.isoformat()))
    return students


def generate_enrollments(students, subjects):
    enrollments = []
    eid = 1
    # Track per-student performance profile for realism
    student_profiles = {}
    for s in students:
        sid = s[0]
        # Base ability: most students are average, some high, some at-risk
        r = random.random()
        if r < 0.12:
            base = random.uniform(2.0, 4.5)  # at-risk
        elif r < 0.30:
            base = random.uniform(8.0, 10.0)  # high performers
        else:
            base = random.uniform(4.5, 8.0)  # average
        student_profiles[sid] = base

    for sem_idx, semester in enumerate(SEMESTERS):
        for s in students:
            sid = s[0]
            dept = s[4]
            base = student_profiles[sid]
            # Each student takes 2-4 subjects per semester
            n_subjects = random.randint(2, 4)
            # Prefer own department subjects but allow cross-dept
            dept_subjects = [sub for sub in subjects if sub[2] == dept]
            other_subjects = [sub for sub in subjects if sub[2] != dept]
            chosen = random.sample(dept_subjects, min(n_subjects, len(dept_subjects)))
            if len(chosen) < n_subjects:
                chosen += random.sample(other_subjects, n_subjects - len(chosen))

            for sub in chosen:
                subj_id = subjects.index(sub) + 1
                # Grade: base +/- noise, trend slightly upward over semesters
                trend = sem_idx * random.uniform(0, 0.3)
                grade = round(min(10.0, max(0.0, base + trend + random.gauss(0, 1.0))), 1)
                # Attendance correlates with grade
                att_base = 50 + (grade / 10.0) * 40 + random.gauss(0, 8)
                attendance = round(min(100.0, max(20.0, att_base)), 2)
                # Assignment and exam scores
                assignment = round(min(100.0, max(0.0, grade * 9 + random.gauss(5, 8))), 2)
                exam = round(min(100.0, max(0.0, grade * 8.5 + random.gauss(0, 10))), 2)
                status = "active" if semester in ("2025-S1", "2025-S2") else "completed"
                if grade < 3.5 and random.random() < 0.08:
                    status = "dropped"
                enrollments.append((eid, sid, subj_id, semester, grade, attendance, assignment, exam, status))
                eid += 1

    return enrollments


def generate_risk_alerts(students, enrollments):
    alerts = []
    aid = 1
    # Index enrollments by student for O(1) lookup
    student_enrollments = {}
    for e in enrollments:
        student_enrollments.setdefault(e[1], []).append(e)

    for s in students:
        sid = s[0]
        enrs = student_enrollments.get(sid, [])
        latest = [e for e in enrs if e[3] == "2025-S2"]
        if not latest:
            latest = [e for e in enrs if e[3] == "2025-S1"]
        for e in latest:
            grade = e[4]
            att = e[5]
            if grade < 4.0:
                alerts.append((aid, sid, "low_grade", "high" if grade < 2.5 else "medium"))
                aid += 1
            if att < 60.0:
                alerts.append((aid, sid, "low_attendance", "high" if att < 40.0 else "medium"))
                aid += 1
            if grade < 5.0 and att < 70.0:
                alerts.append((aid, sid, "combined_risk", "critical"))
                aid += 1
    return alerts


def escape_sql(val):
    if val is None:
        return "NULL"
    if isinstance(val, str):
        return "'" + val.replace("'", "''") + "'"
    return str(val)


def to_sql(students, subjects_data, enrollments, alerts):
    lines = ["-- EduPulse Seed Data (auto-generated)\n"]
    lines.append("-- Students")
    for s in students:
        lines.append(
            f"INSERT INTO students (student_id, name, email, enrollment_year, department, gender, date_of_birth) "
            f"VALUES ({s[0]}, {escape_sql(s[1])}, {escape_sql(s[2])}, {s[3]}, {escape_sql(s[4])}, {escape_sql(s[5])}, {escape_sql(s[6])});"
        )
    lines.append("\n-- Subjects")
    for i, s in enumerate(subjects_data, 1):
        lines.append(
            f"INSERT INTO subjects (subject_id, name, department, credits) "
            f"VALUES ({i}, {escape_sql(s[0])}, {escape_sql(s[1])}, {s[2]});"
        )
    lines.append("\n-- Enrollments")
    for e in enrollments:
        lines.append(
            f"INSERT INTO enrollments (enrollment_id, student_id, subject_id, semester, grade, attendance_pct, assignment_score, exam_score, status) "
            f"VALUES ({e[0]}, {e[1]}, {e[2]}, {escape_sql(e[3])}, {e[4]}, {e[5]}, {e[6]}, {e[7]}, {escape_sql(e[8])});"
        )
    lines.append("\n-- Risk Alerts")
    for a in alerts:
        lines.append(
            f"INSERT INTO risk_alerts (alert_id, student_id, alert_type, severity) "
            f"VALUES ({a[0]}, {a[1]}, {escape_sql(a[2])}, {escape_sql(a[3])});"
        )
    # Reset sequences
    lines.append(f"\nSELECT setval('students_student_id_seq', {len(students)});")
    lines.append(f"SELECT setval('subjects_subject_id_seq', {len(subjects_data)});")
    lines.append(f"SELECT setval('enrollments_enrollment_id_seq', {len(enrollments)});")
    lines.append(f"SELECT setval('risk_alerts_alert_id_seq', {len(alerts)});")
    return "\n".join(lines)


def insert_to_db(students, subjects_data, enrollments, alerts):
    import psycopg2
    conn_str = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/edupulse")
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    for s in students:
        cur.execute(
            "INSERT INTO students (student_id, name, email, enrollment_year, department, gender, date_of_birth) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (student_id) DO NOTHING",
            s,
        )
    for i, s in enumerate(subjects_data, 1):
        cur.execute(
            "INSERT INTO subjects (subject_id, name, department, credits) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (subject_id) DO NOTHING",
            (i, s[0], s[1], s[2]),
        )
    for e in enrollments:
        cur.execute(
            "INSERT INTO enrollments (enrollment_id, student_id, subject_id, semester, grade, attendance_pct, assignment_score, exam_score, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (enrollment_id) DO NOTHING",
            e,
        )
    for a in alerts:
        cur.execute(
            "INSERT INTO risk_alerts (alert_id, student_id, alert_type, severity) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (alert_id) DO NOTHING",
            a,
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted: {len(students)} students, {len(subjects_data)} subjects, "
          f"{len(enrollments)} enrollments, {len(alerts)} risk alerts")


def main():
    parser = argparse.ArgumentParser(description="EduPulse Seed Data Generator")
    parser.add_argument("--sql", action="store_true", help="Output seed_data.sql file")
    parser.add_argument("--db", action="store_true", help="Insert directly into database")
    args = parser.parse_args()

    if not args.sql and not args.db:
        args.sql = True  # Default to SQL output

    students = generate_students(200)
    enrollments = generate_enrollments(students, SUBJECTS)
    alerts = generate_risk_alerts(students, enrollments)

    print(f"Generated: {len(students)} students, {len(SUBJECTS)} subjects, "
          f"{len(enrollments)} enrollments, {len(alerts)} risk alerts")

    if args.sql:
        sql = to_sql(students, SUBJECTS, enrollments, alerts)
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_data.sql")
        with open(out_path, "w") as f:
            f.write(sql)
        print(f"Written to {out_path}")

    if args.db:
        insert_to_db(students, SUBJECTS, enrollments, alerts)


if __name__ == "__main__":
    main()
