"""FirstResponse AI - Flask HTTP server for Cloud Run deployment."""

import json
import os
import traceback

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from google import genai

from agent import TRIAGE_SYSTEM_PROMPT

app = Flask(__name__)
CORS(app)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "firstresponse-ai"}), 200


@app.route("/triage", methods=["POST"])
def triage():
    body = request.get_json(silent=True)
    if not body or not body.get("situation"):
        return jsonify({"error": "Missing 'situation' field in request body"}), 400

    situation = body["situation"].strip()
    if not situation:
        return jsonify({"error": "Situation description cannot be empty"}), 400

    try:
        response = _get_client().models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Triage this emergency situation:\n\n{situation}",
            config=genai.types.GenerateContentConfig(
                system_instruction=TRIAGE_SYSTEM_PROMPT,
                temperature=0.1,
            ),
        )

        text = response.text.strip()
        # Strip markdown code fences if model wraps response
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3].strip()

        result = json.loads(text)
        return jsonify(result), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse triage response", "raw": text}), 502
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Internal server error during triage"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
