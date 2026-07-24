"""
tests/test_date_filter.py

Tests for the Date Filter feature on the /profile route (Step 06).
Covers period shortcuts, custom date ranges, validation errors,
auth guard, and the _date_filter_clause unit helper.
"""

import os
import sqlite3
import tempfile
import pytest

import database.db as db_module
from app import app as flask_app
from database.db import init_db, seed_db
from database.queries import _date_filter_clause


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #

@pytest.fixture()
def app(tmp_path, monkeypatch):
    """
    Patch DB_PATH to a fresh temp file so every test run gets an isolated
    SQLite database.  We call init_db() + seed_db() inside the app context
    after the patch is in place, so the temp DB is fully populated.
    """
    temp_db = str(tmp_path / "test_spendly.db")
    monkeypatch.setattr(db_module, "DB_PATH", temp_db)

    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
    })

    with flask_app.app_context():
        init_db()
        seed_db()
        yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    """
    A test client that is already logged in as the seeded demo user.
    seed_db() creates: email=demo@spendly.com, password=demo123
    """
    resp = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
        follow_redirects=False,
    )
    # Confirm login succeeded — should redirect to /profile
    assert resp.status_code == 302, (
        f"Login failed during fixture setup; status={resp.status_code}"
    )
    return client


# --------------------------------------------------------------------------- #
# Helper                                                                       #
# --------------------------------------------------------------------------- #

def get_profile(client, params=""):
    """GET /profile with optional query string; returns response."""
    url = f"/profile{params}"
    return client.get(url, follow_redirects=False)


# --------------------------------------------------------------------------- #
# Auth guard                                                                   #
# --------------------------------------------------------------------------- #

class TestAuthGuard:
    def test_unauthenticated_request_redirects_to_login(self, client):
        resp = get_profile(client)
        assert resp.status_code == 302, "Expected redirect for unauthenticated request"
        assert "/login" in resp.headers["Location"], (
            "Unauthenticated /profile should redirect to /login"
        )

    def test_unauthenticated_with_period_param_still_redirects(self, client):
        resp = get_profile(client, "?period=last-7")
        assert resp.status_code == 302, "Auth guard must apply even when query params are present"
        assert "/login" in resp.headers["Location"]


# --------------------------------------------------------------------------- #
# Period shortcuts — happy paths                                               #
# --------------------------------------------------------------------------- #

class TestPeriodShortcuts:
    def test_no_params_returns_200(self, auth_client):
        resp = get_profile(auth_client)
        assert resp.status_code == 200, "No params should return 200"

    def test_no_params_shows_profile_page(self, auth_client):
        resp = get_profile(auth_client)
        assert b"Demo User" in resp.data or b"demo" in resp.data.lower(), (
            "Profile page should contain the user's name"
        )

    def test_period_last_7_returns_200(self, auth_client):
        resp = get_profile(auth_client, "?period=last-7")
        assert resp.status_code == 200, "period=last-7 should return 200"

    def test_period_last_30_returns_200(self, auth_client):
        resp = get_profile(auth_client, "?period=last-30")
        assert resp.status_code == 200, "period=last-30 should return 200"

    def test_period_this_month_returns_200(self, auth_client):
        resp = get_profile(auth_client, "?period=this-month")
        assert resp.status_code == 200, "period=this-month should return 200"

    def test_period_last_month_returns_200(self, auth_client):
        resp = get_profile(auth_client, "?period=last-month")
        assert resp.status_code == 200, "period=last-month should return 200"

    def test_period_all_returns_200(self, auth_client):
        resp = get_profile(auth_client, "?period=all")
        assert resp.status_code == 200, "period=all should return 200"

    @pytest.mark.parametrize("period", ["last-7", "last-30", "this-month", "last-month", "all"])
    def test_all_valid_periods_return_200(self, auth_client, period):
        resp = get_profile(auth_client, f"?period={period}")
        assert resp.status_code == 200, f"period={period} should return 200"


# --------------------------------------------------------------------------- #
# Invalid / unknown period — must return 400                                   #
# --------------------------------------------------------------------------- #

class TestInvalidPeriod:
    def test_period_bogus_returns_400(self, auth_client):
        resp = get_profile(auth_client, "?period=bogus")
        assert resp.status_code == 400, "Unknown period value should abort(400)"

    @pytest.mark.parametrize("bad_period", [
        "weekly", "LAST-7", "last7", "30days", "ytd", "forever", "123",
    ])
    def test_various_unknown_periods_return_400(self, auth_client, bad_period):
        resp = get_profile(auth_client, f"?period={bad_period}")
        assert resp.status_code == 400, (
            f"period={bad_period!r} is unknown and should abort(400)"
        )


# --------------------------------------------------------------------------- #
# Custom date range — happy paths                                              #
# --------------------------------------------------------------------------- #

class TestCustomDateRange:
    def test_valid_start_and_end_date_returns_200(self, auth_client):
        resp = get_profile(auth_client, "?start_date=2026-07-01&end_date=2026-07-10")
        assert resp.status_code == 200, "Valid custom date range should return 200"

    def test_only_start_date_returns_200(self, auth_client):
        resp = get_profile(auth_client, "?start_date=2026-07-01")
        assert resp.status_code == 200, "Only start_date should be accepted and return 200"

    def test_only_end_date_returns_200(self, auth_client):
        resp = get_profile(auth_client, "?end_date=2026-07-16")
        assert resp.status_code == 200, "Only end_date should be accepted and return 200"

    def test_custom_date_range_is_passed_to_template(self, auth_client):
        resp = get_profile(auth_client, "?start_date=2026-07-01&end_date=2026-07-10")
        # The route passes raw_start/raw_end to the template as start_date/end_date
        assert b"2026-07-01" in resp.data, (
            "start_date value should be present in the rendered template"
        )
        assert b"2026-07-10" in resp.data, (
            "end_date value should be present in the rendered template"
        )


# --------------------------------------------------------------------------- #
# Custom date range — validation errors                                        #
# --------------------------------------------------------------------------- #

class TestCustomDateValidation:
    def test_invalid_start_date_returns_400(self, auth_client):
        resp = get_profile(auth_client, "?start_date=not-a-date")
        assert resp.status_code == 400, "Malformed start_date should abort(400)"

    def test_invalid_end_date_returns_400(self, auth_client):
        resp = get_profile(auth_client, "?end_date=not-a-date")
        assert resp.status_code == 400, "Malformed end_date should abort(400)"

    @pytest.mark.parametrize("bad_date", [
        "07-01-2026",   # wrong order
        "2026/07/01",   # wrong separator
        "20260701",     # no separator
        "2026-13-01",   # invalid month
        "2026-07-32",   # invalid day
        "yesterday",    # word
        "2026-7-1",     # missing zero-padding
    ])
    def test_various_bad_start_dates_return_400(self, auth_client, bad_date):
        resp = get_profile(auth_client, f"?start_date={bad_date}")
        assert resp.status_code == 400, (
            f"start_date={bad_date!r} should be rejected with 400"
        )

    @pytest.mark.parametrize("bad_date", [
        "07-31-2026",
        "2026/07/31",
        "tomorrow",
        "2026-07-99",
    ])
    def test_various_bad_end_dates_return_400(self, auth_client, bad_date):
        resp = get_profile(auth_client, f"?end_date={bad_date}")
        assert resp.status_code == 400, (
            f"end_date={bad_date!r} should be rejected with 400"
        )

    def test_period_takes_precedence_over_custom_dates(self, auth_client):
        """When period is set, custom date params are ignored; route should not 400."""
        resp = get_profile(auth_client, "?period=last-7&start_date=not-a-date")
        assert resp.status_code == 200, (
            "When a valid period shortcut is given, start_date format is not validated"
        )


# --------------------------------------------------------------------------- #
# Data filtering — verify seed data is actually filtered                       #
# --------------------------------------------------------------------------- #

class TestDataFiltering:
    """
    Seed expenses span 2026-07-01 to 2026-07-16.
    Today is 2026-07-24 per system context.
    We can verify filtering by checking transaction counts / amounts
    via the stats shown in the rendered page, or by asserting specific
    expense descriptions appear / disappear.
    """

    def test_no_filter_shows_all_seed_expenses(self, auth_client):
        """
        Without a filter, all 8 seed expenses should be present.
        The total is 120+500+1850+340+600+950+200+750 = 5310.
        """
        resp = get_profile(auth_client)
        assert resp.status_code == 200
        # Total formatted as ₹5,310.00 must appear somewhere in the page
        assert "5,310.00" in resp.data.decode("utf-8"), (
            "All 8 seed expenses should be included when no filter is applied"
        )

    def test_narrow_date_range_excludes_outside_expenses(self, auth_client):
        """
        Range 2026-07-01 to 2026-07-05 includes:
          120 (Jul 01), 500 (Jul 03), 1850 (Jul 05) → total 2470
        Expenses on Jul 08+ must NOT be counted.
        """
        resp = get_profile(auth_client, "?start_date=2026-07-01&end_date=2026-07-05")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "2,470.00" in body, (
            "Only expenses from Jul 01–05 should be totalled (₹2,470.00)"
        )
        # An expense from outside the range should not appear as a transaction row
        assert "Pharmacy purchase" not in body, (
            "Jul 08 expense should be excluded from the narrow date range"
        )

    def test_single_day_range_shows_only_that_day(self, auth_client):
        """
        Range 2026-07-10 to 2026-07-10 should include only:
          600 (Jul 10, Entertainment, Movie tickets)
        """
        resp = get_profile(auth_client, "?start_date=2026-07-10&end_date=2026-07-10")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "Movie tickets" in body, "Jul 10 expense should appear in single-day filter"
        assert "600.00" in body, "Amount 600.00 should be shown for single-day filter"
        assert "Lunch at office canteen" not in body, (
            "Jul 01 expense must not appear in single-day Jul 10 filter"
        )

    def test_future_date_range_returns_empty_stats(self, auth_client):
        """
        A date range entirely in the future (relative to seed data) returns zero expenses.
        """
        resp = get_profile(auth_client, "?start_date=2027-01-01&end_date=2027-12-31")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "₹0.00" in body, (
            "Future date range with no expenses should show ₹0.00 total"
        )

    def test_only_start_date_filter_includes_from_that_date(self, auth_client):
        """
        start_date=2026-07-12 should include Jul 12, 14, 16 only.
        Total: 950 + 200 + 750 = 1900
        """
        resp = get_profile(auth_client, "?start_date=2026-07-12")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "1,900.00" in body, (
            "start_date=2026-07-12 should total expenses from Jul 12 onwards (₹1,900.00)"
        )

    def test_only_end_date_filter_includes_up_to_that_date(self, auth_client):
        """
        end_date=2026-07-03 should include Jul 01 and Jul 03 only.
        Total: 120 + 500 = 620
        """
        resp = get_profile(auth_client, "?end_date=2026-07-03")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "620.00" in body, (
            "end_date=2026-07-03 should total expenses up to Jul 03 (₹620.00)"
        )


# --------------------------------------------------------------------------- #
# active_period context variable                                               #
# --------------------------------------------------------------------------- #

class TestActivePeriodContext:
    """
    The route passes active_period to the template so the UI can highlight
    the selected filter.  We verify the value appears in the rendered HTML
    (e.g. as a CSS class, data attribute, or option value).
    """

    def test_no_params_active_period_is_all(self, auth_client):
        resp = get_profile(auth_client)
        assert resp.status_code == 200
        # active_period defaults to "all" when no params are given
        assert b"all" in resp.data, (
            "active_period='all' should appear in the rendered page when no filter is given"
        )

    def test_period_last_7_active_period_reflected(self, auth_client):
        resp = get_profile(auth_client, "?period=last-7")
        assert resp.status_code == 200
        assert b"last-7" in resp.data, (
            "active_period='last-7' should appear in the rendered page"
        )

    def test_period_this_month_active_period_reflected(self, auth_client):
        resp = get_profile(auth_client, "?period=this-month")
        assert resp.status_code == 200
        assert b"this-month" in resp.data, (
            "active_period='this-month' should appear in the rendered page"
        )

    def test_custom_dates_active_period_is_custom(self, auth_client):
        resp = get_profile(auth_client, "?start_date=2026-07-01&end_date=2026-07-10")
        assert resp.status_code == 200
        assert b"custom" in resp.data, (
            "active_period='custom' should appear when custom date params are used"
        )


# --------------------------------------------------------------------------- #
# Unit tests: _date_filter_clause                                              #
# --------------------------------------------------------------------------- #

class TestDateFilterClause:
    def test_both_none_returns_empty_clause_and_empty_params(self):
        clause, params = _date_filter_clause(None, None)
        assert clause == "", (
            "_date_filter_clause(None, None) should return empty clause string"
        )
        assert params == (), (
            "_date_filter_clause(None, None) should return empty params tuple"
        )

    def test_start_date_only_returns_gte_clause(self):
        clause, params = _date_filter_clause("2026-07-01", None)
        assert clause == "AND date >= ?", (
            "start_date only should produce 'AND date >= ?' clause"
        )
        assert params == ("2026-07-01",), (
            "start_date only should produce a single-element params tuple"
        )

    def test_end_date_only_returns_lte_clause(self):
        clause, params = _date_filter_clause(None, "2026-07-31")
        assert clause == "AND date <= ?", (
            "end_date only should produce 'AND date <= ?' clause"
        )
        assert params == ("2026-07-31",), (
            "end_date only should produce a single-element params tuple"
        )

    def test_both_dates_returns_combined_clause(self):
        clause, params = _date_filter_clause("2026-07-01", "2026-07-31")
        assert "AND date >= ?" in clause, (
            "Both dates: clause must contain 'AND date >= ?'"
        )
        assert "AND date <= ?" in clause, (
            "Both dates: clause must contain 'AND date <= ?'"
        )
        assert params == ("2026-07-01", "2026-07-31"), (
            "Both dates: params must be (start_date, end_date) in order"
        )

    def test_both_dates_start_comes_before_end_in_params(self):
        _, params = _date_filter_clause("2026-07-01", "2026-07-31")
        assert params[0] == "2026-07-01", "start_date must be first in params tuple"
        assert params[1] == "2026-07-31", "end_date must be second in params tuple"

    def test_return_type_is_tuple_of_str_and_tuple(self):
        result = _date_filter_clause("2026-07-01", "2026-07-31")
        assert isinstance(result, tuple), "_date_filter_clause must return a tuple"
        assert len(result) == 2, "_date_filter_clause must return exactly two elements"
        clause, params = result
        assert isinstance(clause, str), "First element (clause) must be a string"
        assert isinstance(params, tuple), "Second element (params) must be a tuple"

    def test_empty_strings_treated_as_no_filter(self):
        """
        Empty string is falsy in Python, so empty strings should produce no clause,
        same as None.
        """
        clause, params = _date_filter_clause("", "")
        assert clause == "", (
            "Empty string start/end should produce empty clause (falsy check)"
        )
        assert params == (), (
            "Empty string start/end should produce empty params tuple"
        )
