"""MCP Weather Tool Server for AgroAdvisor.

Provides weather data tools via Model Context Protocol using OpenWeatherMap API.
"""

import os
import json
from mcp.server.fastmcp import FastMCP
import httpx

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "demo")
OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"

mcp = FastMCP("weather")


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
        "wind_deg": wind.get("deg"),
        "condition": weather.get("main", "Unknown"),
        "description": weather.get("description", ""),
        "clouds_pct": data.get("clouds", {}).get("all"),
        "visibility_m": data.get("visibility"),
        "rain_1h_mm": data.get("rain", {}).get("1h", 0),
        "rain_3h_mm": data.get("rain", {}).get("3h", 0),
        "uvi": data.get("uvi"),
        "dt": data.get("dt"),
        "location_name": data.get("name", ""),
    }


def _extract_forecast(data: dict) -> dict:
    """Extract relevant fields from 5-day forecast. O(n) over forecast entries only."""
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
            "description": weather.get("description", ""),
            "rain_3h_mm": item.get("rain", {}).get("3h", 0),
            "pop": item.get("pop", 0),  # probability of precipitation 0-1
            "clouds_pct": item.get("clouds", {}).get("all"),
        })

    # Aggregate daily summaries for spraying window analysis
    daily = {}
    for e in entries:
        date = e["dt_txt"][:10] if e.get("dt_txt") else "unknown"
        if date not in daily:
            daily[date] = {
                "date": date,
                "temp_min": e["temperature_c"],
                "temp_max": e["temperature_c"],
                "max_rain_3h_mm": e["rain_3h_mm"],
                "max_pop": e["pop"],
                "max_wind_ms": e["wind_speed_ms"],
                "conditions": set(),
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

    city = data.get("city", {})
    return {
        "location_name": city.get("name", ""),
        "country": city.get("country", ""),
        "daily_summary": daily_list,
        "hourly_entries": entries,
    }


@mcp.tool()
async def get_current_weather(lat: float, lon: float) -> str:
    """Fetch current weather conditions for given coordinates.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        JSON string with temperature, humidity, wind, conditions, rain data.
    """
    url = f"{OPENWEATHER_BASE}/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return json.dumps(_extract_current(data))


@mcp.tool()
async def get_weather_forecast(lat: float, lon: float) -> str:
    """Fetch 5-day / 3-hour weather forecast for given coordinates.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        JSON string with daily summaries and hourly entries including rain probability.
    """
    url = f"{OPENWEATHER_BASE}/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return json.dumps(_extract_forecast(data))


if __name__ == "__main__":
    mcp.run(transport="stdio")
