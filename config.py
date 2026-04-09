import os
from dotenv import load_dotenv
load_dotenv()

# ── Admin ─────────────────────────────────────────────────────────────────────
 
ADMIN_KEY = os.environ.get("CALENDAR_ADMIN_KEY")

# ── Database ──────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "calendar.db")

# ── Fantasy Calendar Constants ────────────────────────────────────────────────

SEASON_NAMES = ["1st", "2nd", "3rd"]
SEASONS_PER_YEAR = 3

MONTH_NAMES = ["Nossus", "Damerus", "Ardus", "Morissus"]
MONTHS_PER_SEASON = 4

WEEKS_PER_MONTH = 4

DAY_NAMES = ["Gotvum", "Chronum", "Tecnum", "Riverum", "Meditum"]
DAYS_PER_WEEK = 5

# ── Derived ───────────────────────────────────────────────────────────────────

TOTAL_DAYS_PER_YEAR = SEASONS_PER_YEAR * MONTHS_PER_SEASON * WEEKS_PER_MONTH * DAYS_PER_WEEK