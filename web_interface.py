from flask import Flask, render_template, request, jsonify, send_file, abort, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import os, json
from datetime import datetime
from mkb_sentinel import QEMESentinelLite, MKBConfig, Sector, ComplianceLevel, quick_gdpr_check

# regulatory: directe checker i.p.v. aparte endpoints-module
from regulatory_integration import MKBRegulatoryChecker

ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
API_TOKEN = os.environ.get("API_TOKEN", "").strip() or None
MAX_JSON_SIZE_KB = int(os.environ.get("MAX_JSON_SIZE_KB", "100"))

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_AS_ASCII"] = False
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}, r"/": {"origins": ALLOWED_ORIGINS}})

REQUEST_COUNT = Counter("sentinel_requests_total", "Total HTTP requests", ["method", "path", "status"])
LAST_HEALTH_OK = Gauge("sentinel_health_ok", "Health status (1 ok, 0 not)")

@app.before_request
def _preflight():
    if request.method in ("POST", "PUT", "PATCH"):
        cl = request.content_length or 0
        if cl > MAX_JSON_SIZE_KB * 1024:
            abort(make_response(jsonify({"error": "Payload too large"}), 413))
    if API_TOKEN and request.path.startswith("/api/"):
        token = request.headers.get("X-API-Token", "")
        if token != API_TOKEN:
            abort(make_response(jsonify({"error": "Unauthorized"}), 401))

@app.after_request
def _security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    try:
        REQUEST_COUNT.labels(request.method, request.path, resp.status_code).inc()
    except Exception:
        pass
    return resp

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/health")
def health():
    LAST_HEALTH_OK.set(1)
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.route("/metrics")
def metrics():
    out = generate_latest()
    resp = make_response(out, 200)
    resp.headers["Content-Type"] = CONTENT_TYPE_LATEST
    return resp

@app.route("/api/quick-scan", methods=["POST"])
def quick_scan():
    try:
        data = request.get_json(force=True, silent=False) or {}
        result = quick_gdpr_check(
            bedrijfsnaam=data.get("bedrijfsnaam", "Test Bedrijf"),
            sector=data.get("sector", "algemeen"),
            prompt=data.get("ai_prompt", "")
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/full-scan", methods=["POST"])
def full_scan():
    try:
        data = request.get_json(force=True, silent=False) or {}

        sector_val = data.get("sector", "algemeen")
        try:
            sector_enum = Sector(sector_val)
        except Exception:
            sector_enum = Sector("algemeen")

        level_val = data.get("compliance_level", "basic")
        try:
            level_enum = ComplianceLevel(level_val)
        except Exception:
            level_enum = ComplianceLevel("basic")

        config = MKBConfig(
            bedrijfsnaam=data.get("bedrijfsnaam"),
            sector=sector_enum,
            compliance_level=level_enum,
            werknemers_aantal=int(data.get("werknemers_aantal", 10)),
            verwerkt_persoonlijke_data=bool(data.get("verwerkt_persoonlijke_data", True)),
            gebruikt_ai=bool(data.get("gebruikt_ai", False)),
            internationale_klanten=bool(data.get("internationale_klanten", False)),
            contact_email=data.get("contact_email", "")
        )

        sentinel = QEMESentinelLite(config)
        user_data = {
            "legal_basis": data.get("legal_basis"),
            "purpose": data.get("purpose"),
            "transfer_country": data.get("transfer_country")
        }

        result = sentinel.run_compliance_scan(
            ai_prompt=data.get("ai_prompt", ""),
            user_data=user_data
        )

        os.makedirs("data", exist_ok=True)
        safe_company = secure_filename((config.bedrijfsnaam or "Bedrijf").replace(" ", "_"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"compliance_rapport_{safe_company}_{timestamp}.json"
        filepath = os.path.abspath(os.path.join("data", filename))

        data_dir = os.path.abspath("data")
        if not filepath.startswith(data_dir + os.sep):
            return jsonify({"error": "Invalid path"}), 400

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        result["rapport_bestand"] = filename
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download-report/<path:filename>")
def download_report(filename):
    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({"error": "Ongeldige bestandsnaam"}), 400
    filepath = os.path.abspath(os.path.join("data", safe_name))
    data_dir = os.path.abspath("data")
    if not filepath.startswith(data_dir + os.sep):
        return jsonify({"error": "Invalid path"}), 400
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "Bestand niet gevonden"}), 404

@app.route("/api/sectors")
def get_sectors():
    return jsonify([{"value": s.value, "label": s.value.title()} for s in Sector])

@app.route("/api/compliance-levels")
def get_compliance_levels():
    return jsonify([
        {"value": "basic", "label": "Basic (€49/maand)", "description": "GDPR basics, ideaal voor starters"},
        {"value": "standard", "label": "Standard (€99/maand)", "description": "GDPR + EU AI Act basics"},
        {"value": "premium", "label": "Premium (€199/maand)", "description": "Volledig compliance pakket"}
    ])

# regulatory: single endpoint (cache by default; use ?refresh=1 to bypass)
@app.route("/api/regulatory-status")
def regulatory_status():
    try:
        refresh = request.args.get("refresh") == "1"
        checker = MKBRegulatoryChecker()
        updates = checker.check_updates(refresh=refresh)
        return jsonify({
            "last_check": datetime.now().isoformat(),
            "total_updates": len(updates),
            "critical_updates": len([u for u in updates if u.impact_level == "critical"]),
            "updates": [
                {
                    "framework": u.framework,
                    "title": u.title,
                    "impact_level": u.impact_level,
                    "summary": u.summary,
                    "url": u.url
                } for u in updates[:5]
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(400)
def bad_request(e): return jsonify({"error": "Bad Request"}), 400

@app.errorhandler(401)
def unauthorized(e): return jsonify({"error": "Unauthorized"}), 401

@app.errorhandler(413)
def too_large(e): return jsonify({"error": "Payload too large"}), 413

@app.errorhandler(404)
def not_found(e): return jsonify({"error": "Not Found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
