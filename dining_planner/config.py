"""Static configuration: API endpoints, scoring weights, campus locations."""

import os

API_BASE_URL = "https://api.hfs.purdue.edu/menus/v2"

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
NUTRITION_CACHE_PATH = os.path.join(CACHE_DIR, "nutrition_cache.json")

# Web app state (per-user settings). Gitignored.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
APP_DB_PATH = os.path.join(DATA_DIR, "app.db")

# Reflects the stated priority order: Nutrition > Time > Proximity.
SCORE_WEIGHTS = {
    "nutrition": 0.6,
    "time": 0.25,
    "proximity": 0.15,
}

# Within the nutrition score: protein (maximize) > calories (stay under cap) > fat (minimize).
NUTRITION_SUBWEIGHTS = {
    "protein": 0.6,
    "calories": 0.25,
    "fat": 0.15,
}

# Default daily goal and day hours, used by the CLI and to seed a new user's saved settings.
DEFAULT_PROTEIN_TARGET_G = 100.0
DEFAULT_CALORIE_LIMIT = 1800.0
DEFAULT_MEALS_PER_DAY = 3
DEFAULT_DAY_START = "07:00"
DEFAULT_DAY_END = "21:00"

# Soft ceiling used to scale the fat penalty; a plate at/above this is treated as fully "bad" on fat.
FAT_SOFT_CEILING_G = 100.0

# Serving sizes that mark an add-on (cheese, sauce, spread) rather than a dish; a plate
# is built around a dish first so a topping's great protein-per-calorie can't crowd it out.
TOPPING_SERVING_SIZES = {"tablespoon", "teaspoon", "ounce", "1 oz serving"}

# A single-meal plate won't have more than this many items suggested.
MAX_PLATE_ITEMS = 6

# Keyword blocklist for the "no beef or pork" dietary restriction. Matched
# case-insensitively against item name + ingredients text.
DEFAULT_RESTRICTED_KEYWORDS = [
    "beef",
    "pork",
    "bacon",
    "ham",
    "sausage",
    "pepperoni",
    "prosciutto",
    "chorizo",
    "salami",
    "carnitas",
    "brisket",
    "pastrami",
    "lard",
    "gelatin",
]

# Buildings you have classes/events in -> (lat, lon). Keys are Purdue building codes;
# an event location like "WALC 2121" matches "WALC". Coordinates from OpenStreetMap.
BUILDING_COORDS: dict[str, tuple[float, float]] = {
    "BHEE": (40.4286, -86.9120),  # Brown Family Hall (the former Electrical Engineering Building)
    "DSAI": (40.4290, -86.9149),  # Hall of Data Science and AI
    "LILY": (40.4232, -86.9183),  # Lilly Hall of Life Sciences
    "LWSN": (40.4278, -86.9170),  # Lawson Hall
    "SMTH": (40.4234, -86.9169),  # Smith Hall
    "WALC": (40.4274, -86.9132),  # Wilmeth Active Learning Center
}

GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials")
CLIENT_SECRET_PATH = os.path.join(CREDENTIALS_DIR, "client_secret.json")
TOKEN_PATH = os.path.join(CREDENTIALS_DIR, "token.json")
# Private iCal feed URL (e.g. Google Calendar's "Secret address in iCal format").
# When present, it's used instead of the Google Calendar API. Gitignored.
CALENDAR_URL_PATH = os.path.join(CREDENTIALS_DIR, "calendar_url.txt")
