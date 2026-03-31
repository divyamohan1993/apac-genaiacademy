"""Tests for FirstResponse AI triage agent and HTTP endpoints."""

import json
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _mock_triage_response(severity, category, transport):
    """Build a mock Gemini response for a given triage level."""
    result = {
        "severity": severity,
        "category": category,
        "confidence": 0.92,
        "symptoms_identified": ["test_symptom"],
        "mechanism_of_injury": "test mechanism",
        "affected_count": 1,
        "immediate_actions": ["Call 911", "Apply pressure"],
        "transport_priority": transport,
        "estimated_resources": {"ems_units": 1, "trauma_centers": 0, "helicopters": 0},
        "rationale": "Test rationale",
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(result)
    return mock_response, result


def _patch_genai():
    """Return a patch that replaces _get_client with a mock."""
    mock_client = MagicMock()
    return patch("app._get_client", return_value=mock_client), mock_client


# --- Endpoint tests ---


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "firstresponse-ai"


def test_index_serves_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"FIRSTRESPONSE" in resp.data


def test_triage_missing_body(client):
    resp = client.post("/triage", content_type="application/json", data="{}")
    assert resp.status_code == 400
    assert "Missing" in resp.get_json()["error"]


def test_triage_empty_situation(client):
    resp = client.post(
        "/triage",
        content_type="application/json",
        data=json.dumps({"situation": "   "}),
    )
    assert resp.status_code == 400
    assert "empty" in resp.get_json()["error"]


# --- Triage classification tests ---


def test_triage_red_immediate(client):
    mock_resp, _ = _mock_triage_response("RED", "IMMEDIATE", "URGENT")
    patcher, mock_client = _patch_genai()
    mock_client.models.generate_content.return_value = mock_resp
    with patcher:
        resp = client.post(
            "/triage",
            content_type="application/json",
            data=json.dumps({"situation": "Car crash victim not breathing, severe bleeding from chest"}),
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["severity"] == "RED"
    assert data["category"] == "IMMEDIATE"
    assert data["transport_priority"] == "URGENT"


def test_triage_yellow_delayed(client):
    mock_resp, _ = _mock_triage_response("YELLOW", "DELAYED", "SOON")
    patcher, mock_client = _patch_genai()
    mock_client.models.generate_content.return_value = mock_resp
    with patcher:
        resp = client.post(
            "/triage",
            content_type="application/json",
            data=json.dumps({"situation": "Person with open fracture on forearm, alert and stable vitals"}),
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["severity"] == "YELLOW"
    assert data["category"] == "DELAYED"


def test_triage_green_minor(client):
    mock_resp, _ = _mock_triage_response("GREEN", "MINOR", "ROUTINE")
    patcher, mock_client = _patch_genai()
    mock_client.models.generate_content.return_value = mock_resp
    with patcher:
        resp = client.post(
            "/triage",
            content_type="application/json",
            data=json.dumps({"situation": "Person with a sprained ankle, walking and talking normally"}),
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["severity"] == "GREEN"
    assert data["category"] == "MINOR"


def test_triage_black_expectant(client):
    mock_resp, _ = _mock_triage_response("BLACK", "EXPECTANT", "NONE")
    patcher, mock_client = _patch_genai()
    mock_client.models.generate_content.return_value = mock_resp
    with patcher:
        resp = client.post(
            "/triage",
            content_type="application/json",
            data=json.dumps({"situation": "Person found with no pulse, not breathing, massive head trauma"}),
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["severity"] == "BLACK"
    assert data["category"] == "EXPECTANT"


def test_response_structure(client):
    mock_resp, _ = _mock_triage_response("RED", "IMMEDIATE", "URGENT")
    patcher, mock_client = _patch_genai()
    mock_client.models.generate_content.return_value = mock_resp
    with patcher:
        resp = client.post(
            "/triage",
            content_type="application/json",
            data=json.dumps({"situation": "Multiple gunshot wounds to abdomen"}),
        )
    data = resp.get_json()
    required_keys = {
        "severity", "category", "confidence", "symptoms_identified",
        "mechanism_of_injury", "affected_count", "immediate_actions",
        "transport_priority", "estimated_resources", "rationale",
    }
    assert required_keys.issubset(data.keys())
    assert isinstance(data["symptoms_identified"], list)
    assert isinstance(data["immediate_actions"], list)
    assert isinstance(data["estimated_resources"], dict)


def test_triage_handles_code_fence_response(client):
    """Test that markdown code fences from the model are stripped."""
    result = {
        "severity": "GREEN",
        "category": "MINOR",
        "confidence": 0.95,
        "symptoms_identified": ["bruise"],
        "mechanism_of_injury": "fall",
        "affected_count": 1,
        "immediate_actions": ["Apply ice"],
        "transport_priority": "ROUTINE",
        "estimated_resources": {"ems_units": 0, "trauma_centers": 0, "helicopters": 0},
        "rationale": "Minor injury",
    }
    mock_response = MagicMock()
    mock_response.text = f"```json\n{json.dumps(result)}\n```"
    patcher, mock_client = _patch_genai()
    mock_client.models.generate_content.return_value = mock_response
    with patcher:
        resp = client.post(
            "/triage",
            content_type="application/json",
            data=json.dumps({"situation": "Kid fell off bike, small bruise on knee"}),
        )
    assert resp.status_code == 200
    assert resp.get_json()["severity"] == "GREEN"
