# Spec: Registration

## Overview

Implement user registration so new visitors can create a Spendly account. This step wires up the existing `POST /register` route stub and `register.html` template (which already has the form UI) to validate input, hash the password, insert a new user row.On success the user is shown a success message and redirected to the login page. It is the first step that writes user-generated data to the database.

## Depends on

- Step 01 — Database Setup (users table must exist)

## Routes

- `GET /register` — render registration form — public (already exists, no change needed)
- `POST /register` — handle form submission, validate, insert user, redirect — public

## Database changes

No new tables or columns. Uses the existing `users` table:

- `name` TEXT NOT NULL
- `email` TEXT NOT NULL UNIQUE
- `password_hash` TEXT NOT NULL

Add a helper function `create_user(name, email, password_hash)` in `database/db.py` that inserts the row and returns the new user id.

## Templates

- **Modify:** `templates/register.html` — add a `confirm_password` field after the `password` field. The form posts to `POST /register` with fields `name`, `email`, `password`, `confirm_password`.

## Files to change

- `app.py` — convert `GET /register` route to handle both GET and POST; add registration logic including confirm password check
- `database/db.py` — add `create_user()` helper function
- `templates/register.html` — add `confirm_password` input field

## Files to create

No new files.

## New dependencies

No new dependencies. Uses:

- `werkzeug.security.generate_password_hash` (already installed)
- `flask.request`, `flask.redirect`, `flask.url_for`, `flask.session` (already installed)

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` before storing
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate server-side: name required, valid email format, password minimum 8 characters, confirm_password must match password
- On duplicate email (UNIQUE constraint violation), catch the `sqlite3.IntegrityError` and re-render the form with `error="An account with that email already exists."`
- After successful registration, redirect to `/login` (do NOT auto-login the user in this step)
- Strip whitespace from `name` and `email` inputs before storing

## Definition of done

- [ ] Visiting `GET /register` renders the registration form with no errors
- [ ] Submitting the form with valid data inserts a new user into the database with a hashed password
- [ ] Submitting with an email that already exists re-renders the form with an error message
- [ ] Submitting with a missing name, email, or password re-renders the form with a validation error
- [ ] Submitting with a password shorter than 8 characters re-renders the form with an error
- [ ] Submitting with mismatched password and confirm password re-renders the form with an error
- [ ] Successful registration redirects to `/login`
- [ ] Password is never stored in plaintext — `password_hash` column contains a werkzeug hash
- [ ] App starts without errors after changes
