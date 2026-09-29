# Web Frontend for the Dining Planner — Design

**Date:** 2026-09-29
**Status:** Draft, awaiting review

## Goal

A desktop web app for the dining planner. It covers ranked meal recommendations and user settings, and is structured so a future native mobile app (React Native / Expo) can reuse the API and the client-side logic. Only the screens would need rewriting.

## Context and constraints

- The existing backend (`dining_planner/`) is a Python library plus a CLI (`main.py`). It has **no HTTP API**, so this work adds one.
- It's used by a single user now, with "others later". v1 has no accounts, but every request is scoped to a `user_id` so accounts can be added without changing routes.
- Calendar access stays file-based in v1 (`credentials/calendar_url.txt` or Google OAuth files), exactly as the CLI uses it today.
- "Extendable for mobile" means a **future native app**. Desktop web is the v1 target, and the narrow-width layout only needs to degrade gracefully.
- v1 screens: **Recommendations** and **Settings**. There's no menu browser or availability editor in v1.

## Architecture

```
dining_planner/          existing engine
  service.py             NEW  plan_day(): orchestration shared by CLI and API
  settings_store.py      NEW  per-user settings persistence (SQLite)
  api/                   NEW  FastAPI app
    app.py               app factory, error handlers, static serving of web/dist
    deps.py              get_current_user() -> "local", shared clients
    schemas.py           Pydantic request/response models
    routes/
      recommendations.py
      settings.py
      meta.py            /meta and /meals
packages/core/           NEW  TypeScript, no React/DOM
  src/types.ts           generated from the OpenAPI schema (openapi-typescript)
  src/client.ts          createApiClient({ baseUrl, fetch })
  src/errors.ts          typed ApiError mapped from error codes
  src/format.ts          pure display helpers
web/                     NEW  Vite + React + TypeScript app, imports @dining/core
```

Frontend packages are managed as an npm workspace (root `package.json` with `workspaces: ["packages/*", "web"]`).

### Changes to existing code

1. **Extract `plan_day()`** from `main.main()` into `dining_planner/service.py`. It covers resolving windows from the calendar, clipping them to now for today, building the per-meal goal, and running the engine. `main.main()` becomes a thin wrapper that prints the result. The existing CLI behavior and `tests/test_main.py` stay green.
2. **Optional meal filter:** `RecommendationEngine.recommend(..., meal_name: Optional[str] = None)` skips any hall meal whose name doesn't match (case-insensitive). The CLI gains a matching `--meal` flag.
3. **Settings-driven config:** `plan_day()` builds the `DietaryFilter` and the engine's `building_coords` from user settings. Both are already injectable, so the engine itself needs no other changes. `config.py` values remain the seed defaults.

## API (`/api/v1`, JSON)

### `GET /settings` · `PUT /settings`

```json
{
  "protein_target_g": 100,
  "calorie_limit": 1800,
  "meals_per_day": 3,
  "day_start": "07:00",
  "day_end": "21:00",
  "restricted_keywords": ["beef", "pork", "..."],
  "building_coords": { "WALC": [40.4274, -86.9132] }
}
```

The first read for a user seeds these from the `config.py` defaults and the CLI's argument defaults. `PUT` replaces the whole object.

Validation rules:
- protein and calories > 0
- `meals_per_day` between 1 and 6
- `day_start` before `day_end`
- latitude in [-90, 90] and longitude in [-180, 180]
- building codes non-empty and uppercased
- keywords non-empty, trimmed, lowercased and deduplicated

### `GET /meals?date=YYYY-MM-DD`

Returns the distinct meal names served that day across all halls, ordered by earliest start time. For example: `["Breakfast", "Lunch", "Late Lunch", "Dinner"]`. `date` defaults to today. This list drives the UI's meal picker, so meal names are never hardcoded.

### `POST /recommendations`

Request: `{ "date"?: "YYYY-MM-DD", "meal"?: string, "protein"?: number, "calories"?: number, "meals"?: number }`. Any goal field that's missing falls back to the user's saved settings.

How date and meal combine:

| date | meal | behavior |
|------|------|----------|
| — | — | Uses the current time: today, with free windows clipped to now, so only meals still reachable today are ranked (all remaining meals). |
| given | — | Ranks every meal that day. It's clipped to now only if the date is today. |
| any | given | Ranks only that meal across halls. If it's today's meal and it has already ended, the response has an empty `recommendations` list and a `notice` such as `"Lunch has ended for today."`. |

Response:
```json
{
  "date": "2026-09-29",
  "meal": null,
  "goal_per_meal": { "protein_g": 33.3, "calories": 600 },
  "windows": [{ "start": "...", "end": "...", "prev_event_location": "WALC 2121", "next_event_location": null }],
  "recommendations": [{
    "rank": 1,
    "dining_hall": "Wiley",
    "meal": "Lunch",
    "window": { "start": "...", "end": "..." },
    "scores": { "total": 0.82, "nutrition": 0.9, "time": 1.0, "proximity": null },
    "plate": [{ "id": "...", "name": "...", "station": "...", "is_vegetarian": false,
                "allergens": [], "nutrition": { "calories": 0, "protein_g": 0, "fat_g": 0, "carbs_g": 0, "serving_size": "" } }]
  }],
  "notice": null,
  "warnings": []
}
```

### `GET /meta`

Returns `{ "calendar_source": "ical" | "google" | "none" }`, so the UI can explain setup up front.

### Errors

Every error uses the shape `{ "error": { "code": string, "message": string, "fields"?: {...} } }`.

| code | status | when |
|------|--------|------|
| `calendar_not_configured` | 409 | No iCal URL file and no Google OAuth credentials |
| `invalid_settings` / `invalid_request` | 422 | Validation failure, with per-field messages |
| `upstream_unavailable` | 502 | The Purdue API or the calendar feed failed or timed out entirely |

A single hall's menu fetch failing is **not** an error. That hall is skipped and named in `warnings`.

### Server concerns

- **User scoping:** `get_current_user()` returns `"local"`. It's the only place to change when accounts arrive.
- **Shared clients:** one `PurdueDiningClient` and hall list are kept per process. The existing on-disk nutrition cache is reused.
- **Settings storage:** SQLite at `data/app.db` (gitignored), in a table `settings(user_id TEXT PRIMARY KEY, json TEXT, updated_at TEXT)`.
- **Serving:** in development, Vite on `:5173` proxies `/api` to uvicorn on `:8000`. In production, FastAPI serves the built `web/dist` from `/`, so everything runs as one process.
- **New Python dependencies:** `fastapi`, `uvicorn`, `httpx` (for tests).

## `packages/core`

This package is plain TypeScript. It has no React and no DOM APIs, so a native app can import it unchanged.

- `types.ts`: generated by `npm run gen:types` from `/openapi.json`. Committed, and regenerated whenever the API changes.
- `client.ts`: `createApiClient({ baseUrl, fetch })` provides `getSettings`, `updateSettings`, `getMeals`, `getMeta` and `getRecommendations`. It throws `ApiError` (with `code`, `message` and `fields`) for any non-2xx response.
- `format.ts`: `formatWindow(start, end)`, `scoreToPercent`, `scoreLabel`, `plateTotals(plate)`, and `goalDelta(totals, goal)`.

## `web/`

The stack is Vite, React, TypeScript, React Router and TanStack Query, styled with CSS modules and design tokens (CSS variables). There's no UI kit.

**Layout:** desktop-first, with a sidebar nav (Recommendations, Settings) and a main content area. At narrow widths the sidebar collapses to a top bar and content goes single-column.

### Recommendations (`/`)

- **Controls:**
  - A date picker, defaulting to today.
  - A meal picker built from `/meals` for the chosen date, defaulting to "Any meal".
  - A "Now" chip that resets date and meal to the current-time default.
  - A collapsible **Goals** row with protein, calories and meals/day. These are prefilled from settings and override them for this query only.
  - Controls are reflected in the URL query string, so a view is linkable and survives a reload.
- **Result cards (ranked):**
  - Each card shows the hall and meal, the free window, a total score, and a breakdown bar for nutrition, time and proximity. When proximity is null it reads "location unknown".
  - Expanding a card shows the plate table: item, station, calories, protein, fat, carbs. A totals row is compared against the per-meal goal.
- **States:**
  - Loading shows skeletons, since fetches can take several seconds.
  - Empty shows the reason, or the `notice` text when there is one.
  - `calendar_not_configured` shows the setup steps.
  - Any other error shows the message and a retry button.
  - Any `warnings` appear as a dismissible banner.

### Settings (`/settings`)

- The form has four sections:
  - **Daily goals:** protein, calories, meals/day.
  - **Day hours:** start and end time.
  - **Dietary restrictions:** keyword chips you can add or remove.
  - **Buildings:** an editable table of code, latitude and longitude.
- Values are validated on the client before saving. Server `fields` errors are shown inline next to the matching fields.
- A successful save invalidates the cached settings and recommendations queries.

### Mobile seam

Screens contain no business logic, only calls to `core` and rendering. A future Expo app would write new screens against the same `createApiClient`, types and formatters.

## Testing

- **Python (pytest, extending `tests/`):**
  - `plan_day()` for each date/meal combination: now-clipping, a future date, and a meal that has ended.
  - The engine's `meal_name` filter.
  - `SettingsStore`: round-trip and seeding against a temp database.
  - API routes via `TestClient`, with dining and calendar clients stubbed and no network access. Covers status codes, error shapes, and fallback to settings.
  - The existing tests stay green.
- **`packages/core` (Vitest):** formatters, and the client's error mapping using a fake `fetch`.
- **`web` (Vitest + Testing Library):**
  - Each Recommendations screen state, against a mocked client.
  - The Settings form's validation and its display of server field errors.
- **Manual end-to-end check:** run both servers and drive the real app with Playwright against live Purdue data before calling the work done.

## Out of scope (v1)

- Accounts, auth, and per-user calendar connection.
- The menu browser and the availability editor.
- A native app and PWA installability.
- Background jobs and precomputation.
