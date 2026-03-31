"""AgroAdvisor - Smart Farming Advisory Agent with MCP weather tools."""

import os
import json
import httpx

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


def _extract_current(data: dict) -> dict:
    """Extract relevant fields from current weather response. O(1) dict lookups."""
    weather = data.get("weather", [{}])[0]
    main = data.get("main", {})
    wind = data.get("wind", {})
    return {
        "temperature_c": main.get("temp"),
        "feels_like_c": main.get("feels_like"),
        "humidity_pct": main.get("humidity"),
        "pressure_hpa": main.get("pressure"),
        "wind_speed_ms": wind.get("speed"),
        "wind_gust_ms": wind.get("gust"),
        "condition": weather.get("main", "Unknown"),
        "description": weather.get("description", ""),
        "clouds_pct": data.get("clouds", {}).get("all"),
        "rain_1h_mm": data.get("rain", {}).get("1h", 0),
        "rain_3h_mm": data.get("rain", {}).get("3h", 0),
        "location_name": data.get("name", ""),
    }


def _extract_forecast(data: dict) -> dict:
    """Extract and aggregate forecast into daily summaries."""
    entries = []
    for item in data.get("list", []):
        main = item.get("main", {})
        weather = item.get("weather", [{}])[0]
        wind = item.get("wind", {})
        entries.append({
            "dt_txt": item.get("dt_txt"),
            "temperature_c": main.get("temp"),
            "humidity_pct": main.get("humidity"),
            "wind_speed_ms": wind.get("speed"),
            "condition": weather.get("main", "Unknown"),
            "rain_3h_mm": item.get("rain", {}).get("3h", 0),
            "pop": item.get("pop", 0),
        })

    daily = {}
    for e in entries:
        date = e["dt_txt"][:10] if e.get("dt_txt") else "unknown"
        if date not in daily:
            daily[date] = {
                "date": date, "temp_min": e["temperature_c"], "temp_max": e["temperature_c"],
                "max_rain_3h_mm": e["rain_3h_mm"], "max_pop": e["pop"],
                "max_wind_ms": e["wind_speed_ms"], "conditions": set(),
            }
        d = daily[date]
        if e["temperature_c"] is not None:
            if d["temp_min"] is None or e["temperature_c"] < d["temp_min"]:
                d["temp_min"] = e["temperature_c"]
            if d["temp_max"] is None or e["temperature_c"] > d["temp_max"]:
                d["temp_max"] = e["temperature_c"]
        d["max_rain_3h_mm"] = max(d["max_rain_3h_mm"] or 0, e["rain_3h_mm"] or 0)
        d["max_pop"] = max(d["max_pop"] or 0, e["pop"] or 0)
        d["max_wind_ms"] = max(d["max_wind_ms"] or 0, e["wind_speed_ms"] or 0)
        d["conditions"].add(e["condition"])

    daily_list = []
    for d in daily.values():
        d["conditions"] = list(d["conditions"])
        daily_list.append(d)

    return {"daily_summary": daily_list, "hourly_entries": entries[:8]}


def get_current_weather(lat: float, lon: float) -> dict:
    """Fetch current weather conditions for given coordinates via OpenWeatherMap API (MCP tool).

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        dict with temperature, humidity, wind, conditions, rain data.
    """
    if not OPENWEATHER_API_KEY:
        return {"error": "OPENWEATHER_API_KEY not configured", "temperature_c": 28, "humidity_pct": 75,
                "condition": "Partly Cloudy", "wind_speed_ms": 2.5, "rain_1h_mm": 0,
                "location_name": "Demo", "description": "demo fallback data"}
    url = f"{OPENWEATHER_BASE}/weather"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    resp = httpx.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return _extract_current(resp.json())


def get_weather_forecast(lat: float, lon: float) -> dict:
    """Fetch 5-day weather forecast for given coordinates via OpenWeatherMap API (MCP tool).

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        dict with daily summaries and hourly entries including rain probability for spraying window analysis.
    """
    if not OPENWEATHER_API_KEY:
        return {"error": "OPENWEATHER_API_KEY not configured", "daily_summary": [
            {"date": "2026-04-01", "temp_min": 24, "temp_max": 32, "max_rain_3h_mm": 0, "max_pop": 0.1, "max_wind_ms": 2, "conditions": ["Clear"]},
            {"date": "2026-04-02", "temp_min": 25, "temp_max": 33, "max_rain_3h_mm": 0, "max_pop": 0.15, "max_wind_ms": 3, "conditions": ["Clouds"]},
            {"date": "2026-04-03", "temp_min": 23, "temp_max": 30, "max_rain_3h_mm": 5, "max_pop": 0.7, "max_wind_ms": 4, "conditions": ["Rain"]},
        ], "hourly_entries": []}
    url = f"{OPENWEATHER_BASE}/forecast"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    resp = httpx.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return _extract_forecast(resp.json())


AGRONOMIST_PROMPT = """You are AgroAdvisor, an expert agronomist AI with deep knowledge of:
- Crop diseases, pests, and nutrient deficiencies across all major crops
- Weather impact on crop health, disease pressure, and pest proliferation
- Integrated Pest Management (IPM) strategies
- Optimal spraying and treatment timing based on weather windows

WORKFLOW:
1. The farmer provides: crop type, growth stage, location (lat/lon), and observed symptoms.
2. Use the get_current_weather tool with the provided lat/lon to fetch real-time weather.
3. Use the get_weather_forecast tool with the same lat/lon to get the 5-day forecast.
4. Analyze the symptoms in context of weather conditions.
5. Identify the most likely disease/pest/issue with confidence level.
6. Determine optimal spraying windows from the forecast data.

RESPONSE FORMAT - You MUST return ONLY valid JSON with this exact structure:
{
  "diagnosis": "Name of the identified disease/pest/deficiency",
  "confidence": 0.85,
  "weather_correlation": "Explanation of how current weather contributes to the issue",
  "treatment_plan": [
    {"step": 1, "action": "Immediate action", "details": "Specific product/method and dosage"},
    {"step": 2, "action": "Follow-up action", "details": "Details with timing"}
  ],
  "spraying_window": [
    {"date": "YYYY-MM-DD", "time_range": "06:00-10:00", "conditions": "Low wind, no rain expected", "suitability": "optimal"},
    {"date": "YYYY-MM-DD", "time_range": "16:00-18:00", "conditions": "Moderate wind", "suitability": "acceptable"}
  ],
  "preventive_measures": [
    "Measure 1 with specific details",
    "Measure 2 with specific details"
  ],
  "weather_summary": {
    "current_temp_c": 28,
    "current_humidity_pct": 85,
    "current_condition": "Partly Cloudy",
    "rain_next_24h": false,
    "forecast_outlook": "Brief 5-day outlook relevant to farming"
  }
}

IMPORTANT: Return ONLY the JSON object. Be specific with treatment products and dosages.
Always consider organic/biological alternatives alongside chemical options.
"""


MODEL = "gemini-2.5-flash"
