# Spec: Login and Logout

## Overview

Implement session-based login and logout so registered users can authenticate and access their account. This step converts the existing `GET /login` stub into a full POST handler that verifies credentials, stores the user id in the Flask session, and redirects to a new `/dashboard` page. The `GET /logout` stub is also wired up to clear the session and return the user to the landing page. A minimal dashboard template is created as the authenticated landing point — it will be expanded in later steps.

## Depends on

- Step 01 — Database Setup (users table must exist)
- Step 02 — Registration (users must be able to create accounts)

## Routes

- `GET /login` — render login form — public (already exists, convert to handle both methods)
- `POST /login` — validate credentials, set session, redirect to dashboard — public
- `GET /logout` — clear session, redirect to landing — logged-in
- `GET /dashboard` — render dashboard page for the logged-in user — logged-in (new route)

## Database changes

No new tables or columns. Add a helper function `get_user_by_email(email)` in `database/db.py` that fetches a single user row by email and returns it (or `None` if not found).

## Templates

- **Create:** `templates/dashboard.html` — minimal authenticated home page showing the logged-in user's name and a sign-out link
- **Modify:** `templates/base.html` — update the nav so it shows a "Sign out" link when `session.user_id` is set and "Sign in" / "Register" links when it is not

## Files to change

- `app.py` — convert `GET /login` to handle GET and POST; add `POST /login` logic; implement `GET /logout`; add `GET /dashboard` route; import `check_password_hash` and `session`
- `database/db.py` — add `get_user_by_email(email)` helper function
- `templates/base.html` — conditionally render nav links based on session state

## Files to create

- `templates/dashboard.html` — minimal dashboard page

## New dependencies

No new dependencies. Uses:

- `werkzeug.security.check_password_hash` (already installed)
- `flask.session` (already installed)

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with werkzeug — use `check_password_hash` to verify, never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Store only `user_id` and `user_name` in the session — never store the password hash or full user object
- After successful login, redirect to `url_for('dashboard')` using `redirect()`
- After logout, redirect to `url_for('landing')` using `redirect()`
- On failed login (wrong email or wrong password), re-render `login.html` with a generic `error` message — do not reveal whether the email or password was wrong (use "Invalid email or password.")
- The dashboard route must check that `session.get('user_id')` is set; if not, redirect to `url_for('login')`
- The logout route must call `session.clear()` before redirecting

## Definition of done

- [ ] Visiting `GET /login` renders the login form
- [ ] Submitting the form with a valid email and correct password sets the session and redirects to `/dashboard`
- [ ] Submitting with an unknown email re-renders the login form with "Invalid email or password."
- [ ] Submitting with a correct email but wrong password re-renders the login form with "Invalid email or password."
- [ ] `GET /dashboard` renders the dashboard template and shows the logged-in user's name
- [ ] Visiting `GET /dashboard` while not logged in redirects to `/login`
- [ ] `GET /logout` clears the session and redirects to the landing page
- [ ] After logout, visiting `/dashboard` redirects to `/login`
- [ ] The nav in `base.html` shows "Sign out" when logged in and "Sign in" / "Register" when logged out
- [ ] The demo user (`demo@spendly.com` / `demo123`) can log in successfully
- [ ] App starts without errors after changes
