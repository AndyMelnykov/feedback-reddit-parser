from datetime import date

from weekutil import iso_week_string


def test_iso_week_string_pads_single_digit_week():
    assert iso_week_string(date(2026, 1, 5)) == "2026-W02"


def test_iso_week_string_double_digit_week():
    assert iso_week_string(date(2026, 8, 15)) == "2026-W33"


def test_iso_week_string_uses_iso_year_across_year_boundary():
    # Dec 29 2025 falls in ISO week 1 of 2026, not week ~52 of 2025.
    assert iso_week_string(date(2025, 12, 29)) == "2026-W01"
