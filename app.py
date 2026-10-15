
from flask import Flask, jsonify, request, send_from_directory
import os
import re

app = Flask(__name__, static_folder="public")


@app.route("/")
def home():
    return send_from_directory("public", "index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "app": "LIVORA",
        "mode": "prototype"
    })


@app.route("/api/blood-banks")
def blood_banks():
    # Demo data only — replace with verified, live data later.
    return jsonify([
        {
            "name": "Demo Blood Bank Kathmandu",
            "location": "Kathmandu, Nepal",
            "phone": "Demo contact — replace with verified number"
        },
        {
            "name": "Demo Blood Bank Pokhara",
            "location": "Pokhara, Nepal",
            "phone": "Demo contact — replace with verified number"
        }
    ])


@app.route("/api/ai/triage", methods=["POST"])
def ai_assistant():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({
            "reply": "Please describe what you need help finding."
        }), 400

    blood_groups = re.findall(
        r"\b(?:AB|A|B|O)\s*[+-]\b",
        message.upper()
    )

    units = re.search(r"\b(\d+)\s+units?\b", message, re.I)
    urgent = any(
        word in message.lower()
        for word in ["urgent", "emergency", "asap", "immediately"]
    )

    details = []

    if blood_groups:
        details.append("Blood group: " + blood_groups[0])

    if units:
        details.append("Units requested: " + units.group(1))

    if urgent:
        details.append("Urgency: urgent")

    if details:
        summary = "\n".join(details)
    else:
        summary = (
            "I couldn't identify a blood group or unit count. "
            "Please include those details if relevant."
        )

    return jsonify({
        "reply": (
            "LIVORA demo assistant\n\n"
            + summary
            + "\n\nThis prototype does not check live blood inventory "
              "or contact blood banks. For a medical emergency, "
              "contact local emergency services or a qualified clinician."
        )
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
