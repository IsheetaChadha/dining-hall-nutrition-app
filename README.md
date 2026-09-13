# Dining Hall Nutrition Planner

Suggests which Purdue dining hall/meal to go to on a given day, ranked by how well it
fits a daily nutrition goal (protein > calorie ceiling > minimizing fat), how well it
fits your Google Calendar availability, and proximity to your other events.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Google Calendar access

1. Create a Google Cloud project and enable the **Google Calendar API**.
2. Create an OAuth client ID of type **Desktop app**, download the JSON, and save it as
   `credentials/client_secret.json` (gitignored).
3. The first time `GoogleCalendarClient` runs, it opens a browser for consent and caches
   a token at `credentials/token.json` (also gitignored) for subsequent runs.

### Campus building coordinates

Edit `dining_planner/config.py` and fill in `BUILDING_COORDS` with the buildings you
actually have classes/events in (name as it appears in your calendar event locations ->
`(lat, lon)`). Any calendar event location not in this map just skips proximity scoring.

## Running

```bash
python -m dining_planner.main
```

## Tests

```bash
pytest
```
