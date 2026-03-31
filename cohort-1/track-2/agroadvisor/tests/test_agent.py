"""Tests for AgroAdvisor - MCP weather tools, HTTP endpoints, validation, response structure."""

import json
import pytest
import sys
import os
from unittest.mock import MagicMock

# Insert project root into path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Test MCP weather extraction functions directly (no ADK dependency)
from mcp_weather import _extract_current, _extract_forecast

# Mock google.adk and google.genai before importing app
_mock_adk = MagicMock()
sys.modules["google.adk"] = _mock_adk
sys.modules["google.adk.agents"] = _mock_adk.agents
sys.modules["google.adk.runners"] = _mock_adk.runners
sys.modules["google.adk.sessions"] = _mock_adk.sessions
sys.modules["google.adk.tools"] = _mock_adk.tools
sys.modules["google.adk.tools.mcp_tool"] = _mock_adk.tools.mcp_tool
sys.modules["google.genai"] = MagicMock()
sys.modules["google.genai.types"] = MagicMock()

from app import app, _resolve_location, _parse_agent_response


# --- Fixtures ---

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


MOCK_CURRENT_WEATHER_RAW = {
    "weather": [{"main": "Clouds", "description": "overcast clouds"}],
    "main": {"temp": 28.5, "feels_like": 31.2, "humidity": 82, "pressure": 1008},
    "wind": {"speed": 2.1, "gust": 4.5, "deg": 180},
    "clouds": {"all": 90},
    "visibility": 8000,
    "rain": {"1h": 0.5, "3h": 1.2},
    "name": "Pune",
    "dt": 1700000000,
}

MOCK_FORECAST_RAW = {
    "city": {"name": "Pune", "country": "IN"},
    "list": [
        {
            "dt_txt": "2026-04-01 06:00:00",
            "main": {"temp": 26.0, "humidity": 78},
            "weather": [{"main": "Rain", "description": "light rain"}],
            "wind": {"speed": 1.5},
            "rain": {"3h": 2.0},
            "pop": 0.8,
            "clouds": {"all": 85},
        },
        {
            "dt_txt": "2026-04-01 12:00:00",
            "main": {"temp": 30.0, "humidity": 65},
            "weather": [{"main": "Clouds", "description": "scattered clouds"}],
            "wind": {"speed": 3.0},
            "rain": {},
            "pop": 0.2,
            "clouds": {"all": 40},
        },
        {
            "dt_txt": "2026-04-02 06:00:00",
            "main": {"temp": 24.0, "humidity": 88},
            "weather": [{"main": "Rain", "description": "moderate rain"}],
            "wind": {"speed": 2.5},
            "rain": {"3h": 5.0},
            "pop": 0.95,
            "clouds": {"all": 100},
        },
    ],
}


# --- Test 1: Extract current weather fields ---

def test_extract_current_weather():
    result = _extract_current(MOCK_CURRENT_WEATHER_RAW)
    assert result["temperature_c"] == 28.5
    assert result["humidity_pct"] == 82
    assert result["wind_speed_ms"] == 2.1
    assert result["condition"] == "Clouds"
    assert result["rain_1h_mm"] == 0.5
    assert result["location_name"] == "Pune"
    assert result["pressure_hpa"] == 1008


# --- Test 2: Extract forecast with daily aggregation ---

def test_extract_forecast():
    result = _extract_forecast(MOCK_FORECAST_RAW)
    assert result["location_name"] == "Pune"
    assert result["country"] == "IN"
    assert len(result["hourly_entries"]) == 3
    assert len(result["daily_summary"]) == 2  # 2 distinct dates

    day1 = result["daily_summary"][0]
    assert day1["date"] == "2026-04-01"
    assert day1["temp_min"] == 26.0
    assert day1["temp_max"] == 30.0
    assert day1["max_pop"] == 0.8
    assert day1["max_rain_3h_mm"] == 2.0


# --- Test 3: Location resolution O(1) lookup ---

def test_resolve_location_known():
    lat, lon = _resolve_location("Pune")
    assert abs(lat - 18.5204) < 0.01
    assert abs(lon - 73.8567) < 0.01


# --- Test 4: Location resolution partial match ---

def test_resolve_location_partial():
    lat, lon = _resolve_location("New Delhi, India")
    assert abs(lat - 28.6139) < 0.01


# --- Test 5: Location resolution unknown falls back to default ---

def test_resolve_location_unknown():
    lat, lon = _resolve_location("xyznonexistent")
    assert lat == 20.5937  # India center default
    assert lon == 78.9629


# --- Test 6: Health endpoint ---

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "agroadvisor"


# --- Test 7: Input validation - missing fields ---

def test_advise_missing_crop(client):
    resp = client.post("/advise", json={"symptoms": "yellow leaves"})
    assert resp.status_code == 400
    assert "crop" in resp.get_json()["error"]


def test_advise_missing_symptoms(client):
    resp = client.post("/advise", json={"crop": "rice", "location": "delhi"})
    assert resp.status_code == 400
    assert "symptoms" in resp.get_json()["error"]


def test_advise_missing_location(client):
    resp = client.post("/advise", json={"crop": "rice", "symptoms": "spots"})
    assert resp.status_code == 400
    assert "location" in resp.get_json()["error"].lower() or "lat" in resp.get_json()["error"].lower()


# --- Test 8: Parse agent response ---

def test_parse_agent_response_clean_json():
    raw = '{"diagnosis": "Blast", "confidence": 0.9}'
    result = _parse_agent_response(raw)
    assert result["diagnosis"] == "Blast"
    assert result["confidence"] == 0.9


def test_parse_agent_response_markdown_fenced():
    raw = '```json\n{"diagnosis": "Blight", "confidence": 0.85}\n```'
    result = _parse_agent_response(raw)
    assert result["diagnosis"] == "Blight"


def test_parse_agent_response_with_surrounding_text():
    raw = 'Here is the advisory:\n{"diagnosis": "Rust", "confidence": 0.7}\nHope this helps!'
    result = _parse_agent_response(raw)
    assert result["diagnosis"] == "Rust"


def test_parse_agent_response_unparseable():
    raw = "Sorry, I cannot help with that."
    result = _parse_agent_response(raw)
    assert "error" in result


# --- Test 9: Index page serves HTML ---

def test_index_serves_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"AgroAdvisor" in resp.data


# --- Test 10: Extract handles missing fields gracefully ---

def test_extract_current_empty():
    result = _extract_current({})
    assert result["condition"] == "Unknown"
    assert result["temperature_c"] is None
    assert result["rain_1h_mm"] == 0


def test_extract_forecast_empty():
    result = _extract_forecast({})
    assert result["location_name"] == ""
    assert result["daily_summary"] == []
    assert result["hourly_entries"] == []
