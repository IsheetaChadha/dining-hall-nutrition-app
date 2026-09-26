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

### Calendar access

**Easiest: private iCal link (no Google Cloud needed).** In Google Calendar on the web, go to
Settings → your calendar → *Integrate calendar* → copy **Secret address in iCal format**
(Outlook/Apple publish links work too), and save it:

```bash
echo 'https://calendar.google.com/calendar/ical/.../basic.ics' > credentials/calendar_url.txt
```

That file is gitignored — treat the URL like a password. When it exists it's used instead of
the Google Calendar API.

**Alternative: Google Calendar API (OAuth).**

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
