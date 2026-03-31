"""
EduPulse - Test Suite
Tests NL-to-SQL, SQL safety, HTTP endpoints, and response structure.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, validate_sql, SCHEMA_CONTEXT


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestSQLValidation:
    def test_valid_select(self):
        sql = validate_sql("SELECT * FROM students LIMIT 10")
        assert sql.startswith("SELECT")

    def test_reject_delete(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_sql("DELETE FROM students WHERE student_id = 1")

    def test_reject_drop(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_sql("DROP TABLE students")

    def test_reject_update(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_sql("UPDATE students SET name = 'x' WHERE student_id = 1")

    def test_reject_insert(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_sql("INSERT INTO students (name) VALUES ('x')")

    def test_reject_truncate(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_sql("TRUNCATE TABLE students")

    def test_reject_non_select(self):
        with pytest.raises(ValueError, match="must be a SELECT"):
            validate_sql("SHOW TABLES")

    def test_strips_markdown_fences(self):
        sql = validate_sql("```sql\nSELECT * FROM students\n```")
        assert sql == "SELECT * FROM students"

    def test_strips_semicolons(self):
        sql = validate_sql("SELECT 1;")
        assert sql == "SELECT 1"


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "edupulse"

    def test_health_db_not_configured(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert "database" in data


class TestIndexEndpoint:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"EduPulse" in resp.data


class TestQueryEndpoint:
    def test_missing_question(self, client):
        resp = client.post("/query", json={})
        assert resp.status_code == 400
        assert "Missing" in resp.get_json()["error"]

    def test_empty_question(self, client):
        resp = client.post("/query", json={"question": "  "})
        assert resp.status_code == 400
        assert "empty" in resp.get_json()["error"]

    @patch("app.nl_to_sql")
    @patch("app.execute_query")
    @patch("app.summarize_results")
    def test_successful_query(self, mock_summary, mock_exec, mock_nl, client):
        mock_nl.return_value = "SELECT name FROM students LIMIT 5"
        mock_exec.return_value = (["name"], [("Aarav Sharma",), ("Priya Patel",)])
        mock_summary.return_value = "Found 2 students."

        resp = client.post("/query", json={"question": "Show me students"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "sql" in data
        assert "columns" in data
        assert "results" in data
        assert "summary" in data
        assert "row_count" in data
        assert "execution_time" in data
        assert data["row_count"] == 2

    @patch("app.nl_to_sql", side_effect=ValueError("Only SELECT queries are permitted."))
    def test_sql_injection_blocked(self, mock_nl, client):
        resp = client.post("/query", json={"question": "DROP TABLE students"})
        assert resp.status_code == 400
        assert "SQL validation" in resp.get_json()["error"]


class TestSchemaContext:
    def test_schema_mentions_all_tables(self):
        for table in ["students", "subjects", "enrollments", "risk_alerts"]:
            assert table in SCHEMA_CONTEXT

    def test_schema_has_safety_rules(self):
        assert "SELECT" in SCHEMA_CONTEXT
        assert "INSERT" in SCHEMA_CONTEXT or "DDL" in SCHEMA_CONTEXT
