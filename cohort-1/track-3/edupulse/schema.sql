-- EduPulse: Student Performance Analytics - Database Schema
-- Designed for AlloyDB for PostgreSQL

CREATE TABLE IF NOT EXISTS students (
    student_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150),
    enrollment_year INT NOT NULL,
    department VARCHAR(50) NOT NULL,
    gender VARCHAR(10),
    date_of_birth DATE
);

CREATE TABLE IF NOT EXISTS subjects (
    subject_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    credits INT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(student_id),
    subject_id INT REFERENCES subjects(subject_id),
    semester VARCHAR(20) NOT NULL,
    grade DECIMAL(3,1),
    attendance_pct DECIMAL(5,2),
    assignment_score DECIMAL(5,2),
    exam_score DECIMAL(5,2),
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS risk_alerts (
    alert_id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(student_id),
    alert_type VARCHAR(50),
    severity VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for O(1) lookups
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_subject ON enrollments(subject_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_semester ON enrollments(semester);
CREATE INDEX IF NOT EXISTS idx_enrollments_status ON enrollments(status);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_student ON risk_alerts(student_id);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_severity ON risk_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_students_department ON students(department);
CREATE INDEX IF NOT EXISTS idx_students_enrollment_year ON students(enrollment_year);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_enrollments_student_semester ON enrollments(student_id, semester);
CREATE INDEX IF NOT EXISTS idx_enrollments_subject_semester ON enrollments(subject_id, semester);
CREATE INDEX IF NOT EXISTS idx_enrollments_grade ON enrollments(grade);
CREATE INDEX IF NOT EXISTS idx_enrollments_attendance ON enrollments(attendance_pct);
