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
actually have classes/events in, keyed by building code (`"WALC"` matches an event
location of `WALC 2121`) -> `(lat, lon)`. Any calendar event location not in this map
just skips proximity scoring.

## Running

### Web app

```bash
npm install                                      # once
python -m uvicorn dining_planner.api.app:app --reload --port 8000   # API
npm run dev:web                                  # web UI at http://localhost:5173
```

Or as one process: `npm run build`, then run only the uvicorn command and open
http://localhost:8000 — the API serves the built app from `web/dist`.

Settings saved in the web app (goals, day hours, foods to avoid, buildings) live in
`data/app.db` (gitignored) and override the defaults in `config.py`.

### CLI

```bash
python -m dining_planner.main
python -m dining_planner.main --meal Dinner --date 2026-09-30
```

## Project layout

- `dining_planner/` — the planner engine; `service.plan_day()` is the entry point
  shared by the CLI and the API.
- `dining_planner/api/` — FastAPI JSON API under `/api/v1` (docs at `/api/docs`).
- `packages/core/` — TypeScript API client, types and formatters with no DOM or React
  dependencies, so a future React Native app can reuse them unchanged.
- `web/` — the React desktop web app.

After changing an API schema, regenerate the client types with `npm run gen:types`.

## Tests

```bash
pytest            # Python engine + API
npm test          # core + web
npm run typecheck
```
