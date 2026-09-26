"""Static configuration: API endpoints, scoring weights, campus locations."""

import os

API_BASE_URL = "https://api.hfs.purdue.edu/menus/v2"

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
NUTRITION_CACHE_PATH = os.path.join(CACHE_DIR, "nutrition_cache.json")

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

# Soft ceiling used to scale the fat penalty; a plate at/above this is treated as fully "bad" on fat.
FAT_SOFT_CEILING_G = 100.0

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

# Fill in with the buildings you actually have classes/events in, as they'll
# appear in your Google Calendar event `location` field.
# Example: "WALC": (40.4249, -86.9151)
BUILDING_COORDS: dict[str, tuple[float, float]] = {}

GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials")
CLIENT_SECRET_PATH = os.path.join(CREDENTIALS_DIR, "client_secret.json")
TOKEN_PATH = os.path.join(CREDENTIALS_DIR, "token.json")
# Private iCal feed URL (e.g. Google Calendar's "Secret address in iCal format").
# When present, it's used instead of the Google Calendar API. Gitignored.
CALENDAR_URL_PATH = os.path.join(CREDENTIALS_DIR, "calendar_url.txt")
