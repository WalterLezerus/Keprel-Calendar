import secrets
import bcrypt
import data_manager
import config


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_user(username: str, password: str):
    """
    Verify credentials and create a session.
    Returns a dict with user info and session token, or None on failure.
    """
    user = data_manager.get_user_by_username(username)
    if not user:
        return None

    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return None

    token = secrets.token_hex(32)
    data_manager.create_session(user["user_id"], token)

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "session_token": token,
    }


def logout_user(token: str):
    """Delete the session token from the DB."""
    data_manager.delete_session(token)


# ── Entry Validation ──────────────────────────────────────────────────────────

REQUIRED_ENTRY_FIELDS = ("title", "year", "season", "month", "week", "day")

def validate_entry_fields(data: dict):
    """
    Check that all required entry fields are present.
    Returns a list of missing field names, empty list if all present.
    """
    if not data:
        return list(REQUIRED_ENTRY_FIELDS)
    return [f for f in REQUIRED_ENTRY_FIELDS if f not in data or data[f] is None]


def valid_date(season=None, month=None, week=None, day=None):
    """
    Validate fantasy calendar date values against configured bounds.
    Only checks the fields that are passed in.
    """
    if season is not None:
        if not (1 <= season <= config.SEASONS_PER_YEAR):
            return False

    if month is not None:
        if not (1 <= month <= config.MONTHS_PER_SEASON):
            return False

    if week is not None:
        if not (1 <= week <= config.WEEKS_PER_MONTH):
            return False

    if day is not None:
        if day not in config.DAY_NAMES:
            return False

    return True


# ── Access Control ────────────────────────────────────────────────────────────

def can_view_entry(user_id: int, entry: dict):
    """
    Return True if the user owns the entry or it has been shared with them.
    """
    if entry["owner_id"] == user_id:
        return True

    shares = data_manager.get_entry_shares(entry["entry_id"])
    return any(s["user_id"] == user_id for s in shares)


# ── User Management (for add_user.py) ────────────────────────────────────────

def create_user(username: str, password: str):
    """
    Hash a password and create a new user.
    Returns the created user dict or None if username already exists.
    """
    existing = data_manager.get_user_by_username(username)
    if existing:
        return None

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return data_manager.create_user(username, password_hash)