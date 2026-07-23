from database.db import get_db
from datetime import datetime


def get_user_by_id(user_id):
    db = get_db()
    try:
        row = db.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        db.close()

    if row is None:
        return None

    name = row["name"]
    initials = "".join(word[0].upper() for word in name.split() if word)
    member_since = datetime.strptime(row["created_at"][:10], "%Y-%m-%d").strftime("%B %Y")

    return {
        "name": name,
        "email": row["email"],
        "initials": initials,
        "member_since": member_since,
    }


def get_summary_stats(user_id):
    db = get_db()
    try:
        totals_row = db.execute(
            "SELECT SUM(amount) as total, COUNT(*) as count FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        category_row = db.execute(
            "SELECT category FROM expenses WHERE user_id = ?"
            " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        db.close()

    total = totals_row["total"] if totals_row and totals_row["total"] is not None else None
    count = totals_row["count"] if totals_row else 0

    return {
        "total_spent": f"₹{total:,.2f}" if total is not None else "₹0.00",
        "transactions": int(count) if count else 0,
        "top_category": category_row["category"] if category_row else "—",
    }


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses"
            " WHERE user_id = ? ORDER BY date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "description": row["description"],
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}",
        }
        for row in rows
    ]


def get_category_breakdown(user_id):
    db = get_db()
    try:
        rows = db.execute(
            "SELECT category, SUM(amount) as total FROM expenses"
            " WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (user_id,),
        ).fetchall()
    finally:
        db.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)

    result = [
        {
            "name": row["category"],
            "amount": f"₹{row['total']:,.2f}",
            "pct": int(round(row["total"] / grand_total * 100)),
        }
        for row in rows
    ]

    pct_sum = sum(item["pct"] for item in result)
    if pct_sum != 100:
        result[0]["pct"] += 100 - pct_sum

    return result
