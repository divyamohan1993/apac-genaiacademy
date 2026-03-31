"""Flask HTTP server for AgroAdvisor agent."""

import os
import json
import traceback
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai

from agent import AGRONOMIST_PROMPT, get_current_weather, get_weather_forecast

app = Flask(__name__)
CORS(app)

_client = None

# O(1) lookup for known crop coordinates
KNOWN_LOCATIONS = {
    "delhi": (28.6139, 77.2090), "new delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777), "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9716, 77.5946), "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867), "kolkata": (22.5726, 88.3639),
    "pune": (18.5204, 73.8567), "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462), "ahmedabad": (23.0225, 72.5714),
    "chandigarh": (30.7333, 76.7794), "patna": (25.6093, 85.1376),
    "bhopal": (23.2599, 77.4126), "nagpur": (21.1458, 79.0882),
    "indore": (22.7196, 75.8577), "coimbatore": (11.0168, 76.9558),
    "bangkok": (13.7563, 100.5018), "jakarta": (-6.2088, 106.8456),
    "manila": (14.5995, 120.9842), "hanoi": (21.0285, 105.8542),
    "tokyo": (35.6762, 139.6503), "beijing": (39.9042, 116.4074),
    "sydney": (-33.8688, 151.2093), "nairobi": (-1.2921, 36.8219),
    "iowa": (41.8780, -93.0977), "california": (36.7783, -119.4179),
    "punjab": (30.7333, 76.7794), "uttar pradesh": (26.8467, 80.9462),
    "maharashtra": (19.7515, 75.7139), "karnataka": (15.3173, 75.7139),
    "tamil nadu": (11.1271, 78.6569), "andhra pradesh": (15.9129, 79.7400),
    "telangana": (18.1124, 79.0193), "west bengal": (22.9868, 87.8550),
    "rajasthan": (27.0238, 74.2179), "madhya pradesh": (22.9734, 78.6569),
    "gujarat": (22.2587, 71.1924), "bihar": (25.0961, 85.3131),
    "kerala": (10.8505, 76.2711),
}


def _resolve_location(location_str: str) -> tuple:
    """Resolve a location string to (lat, lon). O(1) dict lookup."""
    key = location_str.strip().lower()
    if key in KNOWN_LOCATIONS:
        return KNOWN_LOCATIONS[key]
    for k, v in KNOWN_LOCATIONS.items():
        if k in key or key in k:
            return v
    return (20.5937, 78.9629)


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def _parse_agent_response(raw: str) -> dict:
    """Parse agent response, extracting JSON even if wrapped in markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines[1:] if l.strip() != "```"]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"raw_response": raw, "error": "Could not parse structured response"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": "agroadvisor"})


@app.route("/advise", methods=["POST"])
def advise():
    data = request.get_json(force=True)
    crop = data.get("crop", "").strip()
    stage = data.get("stage", "").strip()
    symptoms = data.get("symptoms", "").strip()
    location = data.get("location", "").strip()
    lat = data.get("lat")
    lon = data.get("lon")

    if not crop or not symptoms:
        return jsonify({"error": "crop and symptoms are required"}), 400
    if not stage:
        stage = "unknown"
    if not location and lat is None:
        return jsonify({"error": "Either location or lat/lon coordinates are required"}), 400

    location_name = location
    if lat is not None and lon is not None:
        lat, lon = float(lat), float(lon)
        if not location_name:
            location_name = f"{lat}, {lon}"
    else:
        lat, lon = _resolve_location(location)

    try:
        # Fetch weather data via MCP tools
        current_weather = get_current_weather(lat, lon)
        forecast = get_weather_forecast(lat, lon)

        # Build prompt with weather context
        user_message = (
            f"Crop: {crop}\n"
            f"Growth Stage: {stage}\n"
            f"Location: {location_name} (Lat: {lat}, Lon: {lon})\n"
            f"Observed Symptoms/Concerns: {symptoms}\n\n"
            f"Current Weather Data:\n{json.dumps(current_weather, indent=2)}\n\n"
            f"5-Day Forecast Data:\n{json.dumps(forecast, indent=2)}\n\n"
            f"Based on the above weather data and symptoms, provide your agricultural advisory."
        )

        response = _get_client().models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=genai.types.GenerateContentConfig(
                system_instruction=AGRONOMIST_PROMPT,
                temperature=0.2,
            ),
        )

        result = _parse_agent_response(response.text)
        return jsonify(result)

    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Internal server error during advisory"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
