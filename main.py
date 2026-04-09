from flask import Flask, request, jsonify, render_template, redirect, url_for
import processor
import data_manager
import config

app = Flask(__name__, template_folder="frontend")

with app.app_context():
    data_manager.init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_current_user():
    """Read session cookie and return user dict or None."""
    token = request.cookies.get("session")
    if not token:
        return None
    return data_manager.get_user_by_session(token)


def require_auth():
    """Return (user, error_response) tuple. If error_response is not None, return it immediately."""
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "not authenticated"}), 401)
    return user, None


# ── Page Routes ───────────────────────────────────────────────────────────────

@app.route("/")
def login_page():
    user = get_current_user()
    if user:
        return redirect(url_for("calendar_page"))
    return render_template("login.html")


@app.route("/calendar")
def calendar_page():
    user = get_current_user()
    if not user:
        return redirect(url_for("login_page"))
    return render_template("index.html")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "username and password required"}), 400

    result = processor.login_user(data["username"], data["password"])
    if not result:
        return jsonify({"error": "invalid credentials"}), 401

    response = jsonify({"user_id": result["user_id"], "username": result["username"]})
    response.set_cookie(
        "session",
        result["session_token"],
        httponly=True,
        samesite="Strict"
    )
    return response, 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    user, err = require_auth()
    if err:
        return err

    token = request.cookies.get("session")
    processor.logout_user(token)

    response = jsonify({"message": "logged out"})
    response.delete_cookie("session")
    return response, 200


@app.route("/api/auth/me", methods=["GET"])
def me():
    user, err = require_auth()
    if err:
        return err

    return jsonify({"user_id": user["user_id"], "username": user["username"]}), 200


# ── Calendar Config ───────────────────────────────────────────────────────────

@app.route("/api/calendar/config", methods=["GET"])
def calendar_config():
    user, err = require_auth()
    if err:
        return err

    return jsonify(data_manager.get_calendar_config()), 200


# ── Calendar Views ────────────────────────────────────────────────────────────

@app.route("/api/calendar/year/<int:year>", methods=["GET"])
def calendar_year(year):
    user, err = require_auth()
    if err:
        return err

    data = data_manager.get_year_view(user["user_id"], year)
    return jsonify(data), 200


@app.route("/api/calendar/month/<int:year>/<int:season>/<int:month>", methods=["GET"])
def calendar_month(year, season, month):
    user, err = require_auth()
    if err:
        return err

    if not processor.valid_date(season=season, month=month):
        return jsonify({"error": "invalid season or month"}), 400

    data = data_manager.get_month_view(user["user_id"], year, season, month)
    return jsonify(data), 200


@app.route("/api/calendar/week/<int:year>/<int:season>/<int:month>/<int:week>", methods=["GET"])
def calendar_week(year, season, month, week):
    user, err = require_auth()
    if err:
        return err

    if not processor.valid_date(season=season, month=month, week=week):
        return jsonify({"error": "invalid season, month, or week"}), 400

    data = data_manager.get_week_view(user["user_id"], year, season, month, week)
    return jsonify(data), 200


# ── Entries ───────────────────────────────────────────────────────────────────

@app.route("/api/entries/<int:entry_id>", methods=["GET"])
def get_entry(entry_id):
    user, err = require_auth()
    if err:
        return err

    entry = data_manager.get_entry(entry_id)
    if not entry:
        return jsonify({"error": "entry not found"}), 404

    if not processor.can_view_entry(user["user_id"], entry):
        return jsonify({"error": "access denied"}), 403

    entry["is_owner"] = entry["owner_id"] == user["user_id"]
    entry["shared_with"] = data_manager.get_entry_shares(entry_id)
    return jsonify(entry), 200


@app.route("/api/entries", methods=["POST"])
def create_entry():
    user, err = require_auth()
    if err:
        return err

    data = request.get_json()
    missing = processor.validate_entry_fields(data)
    if missing:
        return jsonify({"error": f"missing required fields: {', '.join(missing)}"}), 400

    if not processor.valid_date(season=data["season"], month=data["month"], week=data["week"], day=data["day"]):
        return jsonify({"error": "invalid date values"}), 400

    entry = data_manager.create_entry(user["user_id"], data)
    return jsonify({"entry_id": entry["entry_id"], "title": entry["title"]}), 201


@app.route("/api/entries/<int:entry_id>", methods=["PUT"])
def edit_entry(entry_id):
    user, err = require_auth()
    if err:
        return err

    entry = data_manager.get_entry(entry_id)
    if not entry:
        return jsonify({"error": "entry not found"}), 404

    if entry["owner_id"] != user["user_id"]:
        return jsonify({"error": "only the owner can edit this entry"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "no data provided"}), 400

    if any(k in data for k in ("season", "month", "week", "day")):
        check = {k: data.get(k, entry[k]) for k in ("season", "month", "week", "day")}
        if not processor.valid_date(**check):
            return jsonify({"error": "invalid date values"}), 400

    updated = data_manager.update_entry(entry_id, data)
    return jsonify({"entry_id": updated["entry_id"], "title": updated["title"]}), 200


@app.route("/api/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    user, err = require_auth()
    if err:
        return err

    entry = data_manager.get_entry(entry_id)
    if not entry:
        return jsonify({"error": "entry not found"}), 404

    if entry["owner_id"] != user["user_id"]:
        return jsonify({"error": "only the owner can delete this entry"}), 403

    data_manager.delete_entry(entry_id)
    return jsonify({"message": "deleted"}), 200


# ── Sharing ───────────────────────────────────────────────────────────────────

@app.route("/api/users/search", methods=["GET"])
def search_users():
    user, err = require_auth()
    if err:
        return err

    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []}), 200

    results = data_manager.search_users(q, exclude_user_id=user["user_id"])
    return jsonify({"results": results}), 200


@app.route("/api/entries/<int:entry_id>/share", methods=["POST"])
def share_entry(entry_id):
    user, err = require_auth()
    if err:
        return err

    entry = data_manager.get_entry(entry_id)
    if not entry:
        return jsonify({"error": "entry not found"}), 404

    if entry["owner_id"] != user["user_id"]:
        return jsonify({"error": "only the owner can share this entry"}), 403

    data = request.get_json()
    if not data or not data.get("user_id"):
        return jsonify({"error": "user_id required"}), 400

    target_user = data_manager.get_user_by_id(data["user_id"])
    if not target_user:
        return jsonify({"error": "user not found"}), 404

    if data_manager.entry_already_shared(entry_id, data["user_id"]):
        return jsonify({"error": "already shared with this user"}), 409

    data_manager.share_entry(entry_id, data["user_id"])
    return jsonify({"message": "shared"}), 200


@app.route("/api/entries/<int:entry_id>/share/<int:target_user_id>", methods=["DELETE"])
def revoke_share(entry_id, target_user_id):
    user, err = require_auth()
    if err:
        return err

    entry = data_manager.get_entry(entry_id)
    if not entry:
        return jsonify({"error": "entry not found"}), 404

    if entry["owner_id"] != user["user_id"]:
        return jsonify({"error": "only the owner can revoke access"}), 403

    data_manager.revoke_share(entry_id, target_user_id)
    return jsonify({"message": "access revoked"}), 200


@app.route("/api/entries/shared-with-me", methods=["GET"])
def shared_with_me():
    user, err = require_auth()
    if err:
        return err

    entries = data_manager.get_shared_with_user(user["user_id"])
    return jsonify({"entries": entries}), 200


# ── Admin ─────────────────────────────────────────────────────────────────────

def require_admin_key(data):
    """Return error response if admin key is missing or wrong, else None."""
    if not config.ADMIN_KEY:
        return jsonify({"error": "admin key not configured on server"}), 500
    if not data or data.get("admin_key") != config.ADMIN_KEY:
        return jsonify({"error": "invalid admin key"}), 403
    return None


@app.route("/api/admin/users", methods=["POST"])
def admin_create_user():
    data = request.get_json()
    err = require_admin_key(data)
    if err:
        return err

    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "username and password required"}), 400

    user = processor.create_user(data["username"], data["password"])
    if not user:
        return jsonify({"error": "username already exists"}), 409

    return jsonify({"user_id": user["user_id"], "username": user["username"]}), 201


@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    data = request.get_json()
    err = require_admin_key(data)
    if err:
        return err

    user = data_manager.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    data_manager.delete_user(user_id)
    return jsonify({"message": "user deleted"}), 200

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)