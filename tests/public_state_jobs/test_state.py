from scripts.public_state_jobs.state import (
    connect,
    init_db,
    upsert_listing,
    select_detail_candidates,
)
from scripts.public_state_jobs.models import ListingSummary


def test_select_candidates_new_no_fp_updated_change_and_ignore_unchanged():
    conn = connect(":memory:")
    init_db(conn)

    # Seed DB: A has fingerprint and updated_at; B missing fingerprint
    upsert_listing(
        conn,
        listing_id="A",
        last_seen_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-10T00:00:00Z",
        detail_fingerprint="fpA",
    )
    upsert_listing(
        conn,
        listing_id="B",
        last_seen_at="2024-01-02T00:00:00Z",
        updated_at="2024-01-05T00:00:00Z",
        detail_fingerprint=None,
    )

    # Summaries, called BEFORE upsert per guidance
    summaries = [
        ListingSummary(listing_id="A", source_url="uA", updated_at="2024-01-10T00:00:00Z"),  # unchanged
        ListingSummary(listing_id="B", source_url="uB", updated_at="2024-01-05T00:00:00Z"),  # no fp
        ListingSummary(listing_id="C", source_url="uC", updated_at="2024-02-01T00:00:00Z"),  # new
        ListingSummary(listing_id="A", source_url="uA", updated_at="2024-01-12T00:00:00Z"),  # updated change
    ]

    results = select_detail_candidates(conn, summaries)
    assert ("B", "no_fingerprint") in results
    assert ("C", "new") in results
    assert ("A", "updated_at_changed") in results
    # Unchanged A should not appear as a candidate
    assert ("A", "") not in results


def test_select_candidates_full_override_returns_full_reason():
    conn = connect(":memory:")
    init_db(conn)

    summaries = [ListingSummary(listing_id="X", source_url="urlX", updated_at=None)]
    results = select_detail_candidates(conn, summaries, full=True)
    assert results == [("X", "full")]

