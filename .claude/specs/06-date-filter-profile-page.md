# Spec: Date Filter for Profile Page

## Overview

This feature adds date range filtering to the Spendly profile page so users can
narrow the transactions table and category breakdown to a specific time window.
After Step 05 wired the profile page to live data, all four profile sections
show everything the user has ever entered. Step 06 lets users slice that data by
date — selecting a preset period (e.g. "Last 30 days", "This month") or typing
custom start/end dates — and immediately see updated transactions and category
totals for the chosen window.

## Depends on

- Step 01 — database schema (expenses.date column in YYYY-MM-DD format)
- Step 05 — profile page backend (get_recent_transactions, get_category_breakdown,
  get_summary_stats helpers in database/queries.py)

## Routes

- `GET /profile` — extended with optional query params `start_date`, `end_date`,
  and `period` — access: logged-in only

No new routes. The existing profile route is updated to read filter params from
`request.args` and forward them to the query helpers.

## Database changes

No database changes. The `expenses.date` TEXT column (YYYY-MM-DD) already exists
and supports range queries with `>=` / `<=` comparisons.

## Templates

- **Modify:** `templates/profile.html`
  - Add a filter bar above the transactions section containing:
    - Preset period buttons: "All time", "Last 7 days", "Last 30 days",
      "This month", "Last month"
    - A collapsible custom date range form with `start_date` and `end_date`
      `<input type="date">` fields and a "Apply" submit button
  - Mark the active preset button with an `active` CSS class
  - Show a plain-text label under the section headings when a filter is active,
    e.g. "Showing results for 1 Jun 2026 – 30 Jun 2026"
  - The filter form submits via `GET` to `url_for('profile')` so the filtered
    URL is bookmarkable and shareable

## Files to change

- `app.py` — update the `profile()` route to read `start_date`, `end_date`, and
  `period` from `request.args`, resolve them to concrete date strings, and pass
  them to query helpers
- `database/queries.py` — update `get_recent_transactions`, `get_summary_stats`,
  and `get_category_breakdown` to accept optional `start_date` and `end_date`
  keyword arguments and add `WHERE date BETWEEN ? AND ?` clauses when provided
- `templates/profile.html` — add filter bar UI (described above)
- `static/css/style.css` — add styles for the filter bar, preset buttons, active
  state, and custom date range form

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never interpolate dates into SQL strings with
  f-strings or `%` formatting
- Passwords hashed with werkzeug (existing behaviour, unchanged)
- Use CSS variables — never hardcode hex values in style.css
- All templates extend `base.html`
- Period resolution belongs in `app.py`, not in templates or query helpers —
  the route converts a `period` shorthand like `last-30` into concrete
  `start_date` / `end_date` strings before calling any helper
- Query helpers must remain backwards-compatible: existing callers that omit
  `start_date` / `end_date` must continue to return all records unchanged
- The "All time" preset must produce the same result as omitting the filter
  entirely (no WHERE clause injected)
- `start_date` and `end_date` values received from query params must be
  validated: they must match `YYYY-MM-DD` format; invalid values should trigger
  `abort(400)`
- The filter bar form method must be `GET`, never `POST`

## Definition of done

- [ ] Visiting `/profile` with no query params shows all transactions and stats
  (unchanged from Step 05 behaviour)
- [ ] Clicking "Last 7 days" reloads the page and shows only expenses whose date
  falls within the last 7 days; the transactions table and category breakdown
  both reflect the filtered data
- [ ] Clicking "Last 30 days" does the same for the past 30 days
- [ ] Clicking "This month" shows only expenses in the current calendar month
- [ ] Clicking "Last month" shows only expenses in the previous calendar month
- [ ] The active preset button is visually distinguished from the inactive ones
- [ ] Submitting the custom date form with a valid start and end date filters all
  three sections (stats, transactions, categories) to that range
- [ ] A filter-active label is displayed beneath the section headings showing the
  resolved date range in human-readable form
- [ ] Submitting the custom date form with a malformed date (e.g. "not-a-date")
  returns HTTP 400
- [ ] The filtered URL (e.g. `/profile?period=last-30`) can be pasted into a new
  tab and produces the same filtered view without re-clicking anything
- [ ] Clicking "All time" clears the filter and returns to the unfiltered view
