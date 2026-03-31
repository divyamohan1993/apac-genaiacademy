"""
EduPulse - Student Performance Analytics
Flask app with Gemini NL-to-SQL conversion over AlloyDB.
"""

import os
import re
import time
import json
import logging

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
from psycopg2 import pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Database connection pool
_db_pool = None

SCHEMA_CONTEXT = """
You are an expert SQL assistant for a student performance analytics database (PostgreSQL).

Tables:
1. students (student_id SERIAL PK, name VARCHAR(100), email VARCHAR(150), enrollment_year INT, department VARCHAR(50), gender VARCHAR(10), date_of_birth DATE)
2. subjects (subject_id SERIAL PK, name VARCHAR(100), department VARCHAR(50), credits INT)
3. enrollments (enrollment_id SERIAL PK, student_id INT FK->students, subject_id INT FK->subjects, semester VARCHAR(20), grade DECIMAL(3,1) [0-10 scale], attendance_pct DECIMAL(5,2) [0-100], assignment_score DECIMAL(5,2) [0-100], exam_score DECIMAL(5,2) [0-100], status VARCHAR(20) [active/completed/dropped])
4. risk_alerts (alert_id SERIAL PK, student_id INT FK->students, alert_type VARCHAR(50) [low_grade/low_attendance/combined_risk], severity VARCHAR(20) [medium/high/critical], created_at TIMESTAMP)

Semesters: '2024-S1', '2024-S2', '2025-S1', '2025-S2'
Departments: 'Computer Science', 'Mathematics', 'Physics', 'Business'
Grade scale: 0.0-10.0 (below 4.0 is at-risk/failing)

Rules:
- Generate ONLY a single SELECT statement. No INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or any DDL/DML.
- Do NOT use semicolons.
- Use proper JOINs when querying across tables.
- Limit results to 50 rows max unless the user asks for a specific count.
- Return ONLY the raw SQL, no explanation, no markdown, no code fences.
"""


def get_db_pool():
    global _db_pool
    if _db_pool is None:
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            # Try Cloud SQL socket connection
            instance = os.environ.get("CLOUD_SQL_INSTANCE", "")
            db_name = os.environ.get("DB_NAME", "edupulse")
            db_user = os.environ.get("DB_USER", "edupulse")
            db_pass = os.environ.get("DB_PASS", "")
            if instance and db_pass:
                db_url = f"host=/cloudsql/{instance} dbname={db_name} user={db_user} password={db_pass}"
            else:
                return None
        _db_pool = pool.ThreadedConnectionPool(1, 10, db_url)
    return _db_pool


def get_db_connection():
    p = get_db_pool()
    if p is None:
        return None
    return p.getconn()


def release_db_connection(conn):
    p = get_db_pool()
    if p and conn:
        p.putconn(conn)


def validate_sql(sql):
    """Reject anything that is not a SELECT statement."""
    cleaned = sql.strip().rstrip(";").strip()
    # Remove markdown code fences if Gemini wraps them
    cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    forbidden = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b",
        re.IGNORECASE,
    )
    if forbidden.search(cleaned):
        raise ValueError("Only SELECT queries are permitted.")
    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        raise ValueError("Query must be a SELECT statement.")
    return cleaned


def nl_to_sql(question):
    """Use Gemini to convert a natural language question to SQL."""
    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{SCHEMA_CONTEXT}\n\nConvert this question to a PostgreSQL SELECT query:\n{question}",
    )
    raw_sql = response.text.strip()
    return validate_sql(raw_sql)


def summarize_results(question, sql, results, columns):
    """Use Gemini to produce a natural language summary of query results."""
    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=api_key)

    # Truncate results for context window
    display_results = results[:30]
    results_text = json.dumps(
        [dict(zip(columns, row)) for row in display_results], indent=2, default=str
    )
    prompt = (
        f"The user asked: \"{question}\"\n"
        f"SQL executed: {sql}\n"
        f"Results ({len(results)} rows, showing up to 30):\n{results_text}\n\n"
        f"Provide a concise, helpful natural language summary of these results. "
        f"Highlight key insights, patterns, or concerning trends. Be specific with numbers. "
        f"Keep it to 2-4 sentences."
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()


def execute_query(sql):
    """Execute a validated SELECT query and return results."""
    conn = get_db_connection()
    if conn is None:
        raise ConnectionError("Database not configured. Set DATABASE_URL environment variable.")
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        cur.close()
        return columns, rows
    finally:
        release_db_connection(conn)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    status = {"status": "healthy", "service": "edupulse"}
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            release_db_connection(conn)
            status["database"] = "connected"
        else:
            status["database"] = "not_configured"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
    return jsonify(status)


@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field"}), 400

    question = data["question"].strip()
    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    start = time.time()
    try:
        sql = nl_to_sql(question)
        columns, rows = execute_query(sql)
        # Convert rows to serializable format
        serializable_rows = []
        for row in rows:
            serializable_rows.append(
                [float(v) if isinstance(v, __import__("decimal").Decimal) else
                 v.isoformat() if hasattr(v, "isoformat") else v
                 for v in row]
            )
        elapsed = round(time.time() - start, 3)
        summary = summarize_results(question, sql, serializable_rows, columns)
        return jsonify({
            "sql": sql,
            "columns": columns,
            "results": serializable_rows[:50],
            "summary": summary,
            "row_count": len(rows),
            "execution_time": elapsed,
        })
    except ValueError as e:
        return jsonify({"error": f"SQL validation error: {str(e)}"}), 400
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception("Query failed")
        return jsonify({"error": f"Query failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
