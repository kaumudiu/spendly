import os
import sqlite3
from datetime import date, timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def resolve_date_filter(period, raw_start, raw_end):
    """Return (start_date, end_date, active_period) as ISO strings or None.
    Calls abort(400) on invalid input."""
    today = date.today()
    active_period = period or ("custom" if raw_start or raw_end else "all")

    if period == "last-7":
        return (today - timedelta(days=6)).isoformat(), today.isoformat(), active_period
    if period == "last-30":
        return (today - timedelta(days=29)).isoformat(), today.isoformat(), active_period
    if period == "this-month":
        return today.replace(day=1).isoformat(), today.isoformat(), active_period
    if period == "last-month":
        first_of_this = today.replace(day=1)
        last_of_prev  = first_of_this - timedelta(days=1)
        return last_of_prev.replace(day=1).isoformat(), last_of_prev.isoformat(), active_period
    if period not in ("all", ""):
        abort(400)

    start_date = end_date = None
    if not period:
        for raw in (raw_start, raw_end):
            if raw:
                try:
                    parsed = datetime.strptime(raw, "%Y-%m-%d")
                    if parsed.strftime("%Y-%m-%d") != raw:
                        abort(400)
                except ValueError:
                    abort(400)
        start_date = raw_start or None
        end_date   = raw_end or None

    return start_date, end_date, active_period


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")

    name             = request.form.get("name", "").strip()
    email            = request.form.get("email", "").strip()
    password         = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name:
        return render_template("register.html", error="Full name is required.")
    if not email:
        return render_template("register.html", error="Email address is required.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")
    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    password_hash = generate_password_hash(password)

    try:
        create_user(name, email, password_hash)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.")

    flash("Account created! You can now sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session.clear()
    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]

    user = get_user_by_id(uid)
    if user is None:
        abort(404)

    period    = request.args.get("period", "").strip()
    raw_start = request.args.get("start_date", "").strip()
    raw_end   = request.args.get("end_date", "").strip()

    start_date, end_date, active_period = resolve_date_filter(period, raw_start, raw_end)

    stats      = get_summary_stats(uid, start_date, end_date)
    expenses   = get_recent_transactions(uid, start_date=start_date, end_date=end_date)
    categories = get_category_breakdown(uid, start_date, end_date)

    return render_template("profile.html",
                           user=user,
                           stats=stats,
                           expenses=expenses,
                           categories=categories,
                           active_period=active_period,
                           start_date=raw_start,
                           end_date=raw_end)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
