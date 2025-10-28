# app.py
import os
import logging
from flask import Flask, request, jsonify, abort
import tinytuya

from prometheus_exporter import collect_metrics

# --- Logging ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tuya-bridge")

# --- Config from env ---
TINYTUYA_REGION = os.getenv("TINYTUYA_REGION", "eu")  # eu, us, cn, in
TINYTUYA_API_KEY = os.getenv("TINYTUYA_API_KEY")
TINYTUYA_API_SECRET = os.getenv("TINYTUYA_API_SECRET")
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "change-me")  # used by clients (HA)

if not (TINYTUYA_API_KEY and TINYTUYA_API_SECRET):
    log.error("Missing TINYTUYA_API_KEY or TINYTUYA_API_SECRET environment variables.")
    raise SystemExit("Missing Tuya credentials")

# --- Initialize Cloud client (tinytuya handles tokens internally) ---
log.info("Initializing TinyTuya Cloud client for region=%s", TINYTUYA_REGION)
cloud = tinytuya.Cloud(
    apiRegion=TINYTUYA_REGION, apiKey=TINYTUYA_API_KEY, apiSecret=TINYTUYA_API_SECRET
)

# --- Flask app ---
app = Flask(__name__)


def check_auth():
    token = request.headers.get("X-API-KEY", "")
    if token != SERVICE_API_KEY:
        abort(401, "invalid api key")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "region": TINYTUYA_REGION})


@app.route("/devices", methods=["GET"])
def list_devices():
    check_auth()
    try:
        devices = cloud.getdevices()
        return jsonify({"success": True, "devices": devices})
    except Exception as e:
        log.exception("Failed to list devices")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/devices/<device_id>/status", methods=["GET"])
def device_status(device_id):
    check_auth()
    try:
        status = cloud.getstatus(device_id)
        return jsonify({"success": True, "status": status})
    except Exception as e:
        log.exception("Failed to get status for %s", device_id)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/devices/<device_id>/functions", methods=["GET"])
def device_functions(device_id):
    check_auth()
    try:
        funcs = cloud.getfunctions(device_id)
        return jsonify({"success": True, "functions": funcs})
    except Exception as e:
        log.exception("Failed to get functions for %s", device_id)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/devices/<device_id>/commands", methods=["POST"])
def device_commands(device_id):
    check_auth()
    body = request.get_json(silent=True) or {}
    commands = body.get("commands")
    if not commands:
        return (
            jsonify(
                {"success": False, "error": "missing 'commands' list in JSON body"}
            ),
            400,
        )

    # commands is expected to be a list like: [{"code":"switch_1","value":true}, ...]
    payload = {"commands": commands}
    try:
        res = cloud.sendcommand(device_id, payload)
        return jsonify({"success": True, "result": res})
    except Exception as e:
        log.exception("Failed to send command to %s: %s", device_id, e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/metrics", defaults={"device_id": "bfe98afa941d5a1e2def8s"})
@app.route("/metrics/<device_id>", methods=["GET"])
def metrics(device_id):
    result = collect_metrics(cloud, device_id)
    return result


# simple root
@app.route("/", methods=["GET"])
def index():
    return jsonify({"service": "tuya-bridge", "version": "1.0"})


if __name__ == "__main__":
    # For local testing only. In k8s we'll use gunicorn in the container.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
