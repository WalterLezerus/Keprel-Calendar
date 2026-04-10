from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, User, Session, Entry, Share
import config

engine = create_engine(f"sqlite:///{config.DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)


def get_db():
    """Return a new DB session."""
    return SessionLocal()


# ── Users ─────────────────────────────────────────────────────────────────────

def get_user_by_username(username: str):
    db = get_db()
    try:
        user = db.query(User).filter(User.username == username).first()
        return _user_dict(user)
    finally:
        db.close()


def get_user_by_id(user_id: int):
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return _user_dict(user)
    finally:
        db.close()


def search_users(q: str, exclude_user_id: int):
    db = get_db()
    try:
        users = (
            db.query(User)
            .filter(User.username.ilike(f"%{q}%"))
            .filter(User.id != exclude_user_id)
            .all()
        )
        return [{"user_id": u.id, "username": u.username} for u in users]
    finally:
        db.close()


def create_user(username: str, password_hash: str):
    db = get_db()
    try:
        user = User(username=username, password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        return _user_dict(user)
    finally:
        db.close()


def delete_user(user_id: int):
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()


# ── Sessions ──────────────────────────────────────────────────────────────────

def get_user_by_session(token: str):
    db = get_db()
    try:
        session = db.query(Session).filter(Session.token == token).first()
        if not session:
            return None
        user = db.query(User).filter(User.id == session.user_id).first()
        return _user_dict(user)
    finally:
        db.close()

def delete_sessions_for_user(user_id: int):
    db = get_db()
    try:
        db.query(Session).filter(Session.user_id == user_id).delete()
        db.commit()
    finally:
        db.close()


def create_session(user_id: int, token: str):
    db = get_db()
    try:
        session = Session(user_id=user_id, token=token)
        db.add(session)
        db.commit()
    finally:
        db.close()


def delete_session(token: str):
    db = get_db()
    try:
        db.query(Session).filter(Session.token == token).delete()
        db.commit()
    finally:
        db.close()


# ── Calendar Config ───────────────────────────────────────────────────────────

def get_calendar_config():
    return {
        "seasons": config.SEASON_NAMES,
        "months_per_season": config.MONTHS_PER_SEASON,
        "weeks_per_month": config.WEEKS_PER_MONTH,
        "days": config.DAY_NAMES,
        "month_names": config.MONTH_NAMES,
    }


# ── Calendar Views ────────────────────────────────────────────────────────────

def get_year_view(user_id: int, year: int):
    db = get_db()
    try:
        accessible = _accessible_entry_ids(db, user_id)
        result = {"year": year, "seasons": {}}

        for season_num in range(1, config.SEASONS_PER_YEAR + 1):
            count = (
                db.query(Entry)
                .filter(
                    Entry.id.in_(accessible),
                    Entry.year == year,
                    Entry.season == season_num,
                )
                .count()
            )
            result["seasons"][str(season_num)] = {"entry_count": count}

        return result
    finally:
        db.close()


def get_month_view(user_id: int, year: int, season: int, month: int):
    db = get_db()
    try:
        accessible = _accessible_entry_ids(db, user_id)
        entries = (
            db.query(Entry)
            .filter(
                Entry.id.in_(accessible),
                Entry.year == year,
                Entry.season == season,
                Entry.month == month,
            )
            .all()
        )

        weeks = {}
        for week_num in range(1, config.WEEKS_PER_MONTH + 1):
            weeks[str(week_num)] = {day: [] for day in config.DAY_NAMES}

        for e in entries:
            weeks[str(e.week)][e.day].append({"entry_id": e.id, "title": e.title})

        return {"year": year, "season": season, "month": month, "weeks": weeks}
    finally:
        db.close()


def get_week_view(user_id: int, year: int, season: int, month: int, week: int):
    db = get_db()
    try:
        accessible = _accessible_entry_ids(db, user_id)
        entries = (
            db.query(Entry)
            .filter(
                Entry.id.in_(accessible),
                Entry.year == year,
                Entry.season == season,
                Entry.month == month,
                Entry.week == week,
            )
            .all()
        )

        days = {day: [] for day in config.DAY_NAMES}
        for e in entries:
            days[e.day].append({"entry_id": e.id, "title": e.title, "time": e.time})

        return {"year": year, "season": season, "month": month, "week": week, "days": days}
    finally:
        db.close()


# ── Entries ───────────────────────────────────────────────────────────────────

def get_entry(entry_id: int):
    db = get_db()
    try:
        entry = db.query(Entry).filter(Entry.id == entry_id).first()
        return _entry_dict(entry)
    finally:
        db.close()


def create_entry(user_id: int, data: dict):
    db = get_db()
    try:
        entry = Entry(
            owner_id=user_id,
            title=data["title"],
            description=data.get("description"),
            time=data.get("time"),
            year=data["year"],
            season=data["season"],
            month=data["month"],
            week=data["week"],
            day=data["day"],
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _entry_dict(entry)
    finally:
        db.close()


def update_entry(entry_id: int, data: dict):
    db = get_db()
    try:
        entry = db.query(Entry).filter(Entry.id == entry_id).first()
        updatable = ("title", "description", "time", "year", "season", "month", "week", "day")
        for field in updatable:
            if field in data:
                setattr(entry, field, data[field])
        db.commit()
        db.refresh(entry)
        return _entry_dict(entry)
    finally:
        db.close()


def delete_entry(entry_id: int):
    db = get_db()
    try:
        db.query(Share).filter(Share.entry_id == entry_id).delete()
        db.query(Entry).filter(Entry.id == entry_id).delete()
        db.commit()
    finally:
        db.close()


# ── Sharing ───────────────────────────────────────────────────────────────────

def get_entry_shares(entry_id: int):
    db = get_db()
    try:
        shares = db.query(Share).filter(Share.entry_id == entry_id).all()
        result = []
        for s in shares:
            user = db.query(User).filter(User.id == s.shared_with_user_id).first()
            if user:
                result.append({"user_id": user.id, "username": user.username})
        return result
    finally:
        db.close()


def entry_already_shared(entry_id: int, user_id: int):
    db = get_db()
    try:
        return db.query(Share).filter(
            Share.entry_id == entry_id,
            Share.shared_with_user_id == user_id
        ).first() is not None
    finally:
        db.close()


def share_entry(entry_id: int, user_id: int):
    db = get_db()
    try:
        share = Share(entry_id=entry_id, shared_with_user_id=user_id)
        db.add(share)
        db.commit()
    finally:
        db.close()


def revoke_share(entry_id: int, user_id: int):
    db = get_db()
    try:
        db.query(Share).filter(
            Share.entry_id == entry_id,
            Share.shared_with_user_id == user_id
        ).delete()
        db.commit()
    finally:
        db.close()


def get_shared_with_user(user_id: int):
    db = get_db()
    try:
        shares = db.query(Share).filter(Share.shared_with_user_id == user_id).all()
        result = []
        for s in shares:
            entry = db.query(Entry).filter(Entry.id == s.entry_id).first()
            if entry:
                result.append({
                    "entry_id": entry.id,
                    "title": entry.title,
                    "owner_id": entry.owner_id,
                    "year": entry.year,
                    "season": entry.season,
                    "month": entry.month,
                    "week": entry.week,
                    "day": entry.day,
                })
        return result
    finally:
        db.close()


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _accessible_entry_ids(db, user_id: int):
    """Return a list of entry IDs the user owns or has been shared with."""
    owned = [e.id for e in db.query(Entry.id).filter(Entry.owner_id == user_id).all()]
    shared = [s.entry_id for s in db.query(Share.entry_id).filter(Share.shared_with_user_id == user_id).all()]
    return list(set(owned + shared))


def _user_dict(user):
    if not user:
        return None
    return {"user_id": user.id, "username": user.username, "password_hash": user.password_hash}


def _entry_dict(entry):
    if not entry:
        return None
    return {
        "entry_id": entry.id,
        "title": entry.title,
        "description": entry.description,
        "time": entry.time,
        "year": entry.year,
        "season": entry.season,
        "month": entry.month,
        "week": entry.week,
        "day": entry.day,
        "owner_id": entry.owner_id,
    }