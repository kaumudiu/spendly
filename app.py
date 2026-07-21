import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


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

    user = {
        "name":         "Alex Morgan",
        "email":        "alex@example.com",
        "initials":     "AM",
        "member_since": "March 2024",
    }

    stats = {
        "total_spent":  "₹5,310",
        "transactions": 8,
        "top_category": "Bills",
    }

    expenses = [
        {"date": "16 Jul 2026", "description": "Dinner with friends", "category": "Food",          "amount": "₹750.00"},
        {"date": "14 Jul 2026", "description": "Miscellaneous",       "category": "Other",         "amount": "₹200.00"},
        {"date": "12 Jul 2026", "description": "Grocery run",         "category": "Shopping",      "amount": "₹950.00"},
        {"date": "10 Jul 2026", "description": "Movie tickets",       "category": "Entertainment", "amount": "₹600.00"},
        {"date": "08 Jul 2026", "description": "Pharmacy purchase",   "category": "Health",        "amount": "₹340.00"},
    ]

    categories = [
        {"name": "Bills",         "amount": "₹1,850", "percent": 100},
        {"name": "Shopping",      "amount": "₹950",   "percent": 51},
        {"name": "Food",          "amount": "₹870",   "percent": 47},
        {"name": "Entertainment", "amount": "₹600",   "percent": 32},
        {"name": "Transport",     "amount": "₹500",   "percent": 27},
        {"name": "Health",        "amount": "₹340",   "percent": 18},
        {"name": "Other",         "amount": "₹200",   "percent": 11},
    ]

    return render_template("profile.html",
                           user=user,
                           stats=stats,
                           expenses=expenses,
                           categories=categories)


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
    app.run(debug=True, port=5001)
