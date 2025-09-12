from scripts.public_state_jobs.salary_parse import parse_salary_text


def test_salary_range_en_dash_and_thousand_separators():
    lo, hi = parse_salary_text("Lønn: kr 600 000 – 750 000 per år")
    assert (lo, hi) == (600000, 750000)


def test_salary_single_value_with_dot_separator():
    lo, hi = parse_salary_text("Lønn: kr 650.000")
    assert (lo, hi) == (650000, 650000)


def test_salary_qualitative_returns_none():
    assert parse_salary_text("Lønn etter avtale") == (None, None)


def test_salary_requires_currency_context():
    # Should not parse a bare number lacking kr/nok
    assert parse_salary_text("Lønn 500 000") == (None, None)
    # But NOK counts as currency marker
    assert parse_salary_text("NOK 500 000") == (500000, 500000)
