from scripts.public_state_jobs.models import ExplodedJobRow, ListingSummary
from scripts.public_state_jobs.models import to_exploded_dataframe
from scripts.public_state_jobs.validation import compute_exploded_metrics, measure_incremental_efficiency
from scripts.public_state_jobs.state import connect, init_db


def test_compute_exploded_metrics_schema_and_presence():
    rows = [
        ExplodedJobRow(
            listing_id="L1",
            job_code="1234",
            job_title=None,
            employer_normalized="forsvaret",
            salary_min=600000,
            salary_max=700000,
            salary_text="600000–700000",
            is_shared_salary=True,
            published_at=None,
            updated_at=None,
            apply_deadline=None,
            source_url="https://x/L1",
        ),
        ExplodedJobRow(
            listing_id="L2",
            job_code="5678",
            job_title=None,
            employer_normalized="pst",
            salary_min=None,
            salary_max=None,
            salary_text=None,
            is_shared_salary=False,
            published_at=None,
            updated_at=None,
            apply_deadline=None,
            source_url="https://x/L2",
        ),
    ]
    df = to_exploded_dataframe([r.to_dict() for r in rows])
    m = compute_exploded_metrics(df)
    assert m["total_rows"] == 2
    assert m["codes_present"] == 2 and m["schema_ok"] is True
    assert m["salary_any_present"] == 1 and 0.49 < m["salary_any_pct"] < 0.51


def test_measure_incremental_efficiency_reduction():
    conn = connect(":memory:")
    init_db(conn)
    # Run 1: A, B new
    run1 = [
        ListingSummary(listing_id="A", source_url="https://x/detail/A", updated_at="2024-01-01T00:00:00Z"),
        ListingSummary(listing_id="B", source_url="https://x/detail/B", updated_at="2024-01-01T00:00:00Z"),
    ]
    # Run 2: A,B unchanged (fingerprinted), C new
    run2 = [
        ListingSummary(listing_id="A", source_url="https://x/detail/A", updated_at="2024-01-01T00:00:00Z"),
        ListingSummary(listing_id="B", source_url="https://x/detail/B", updated_at="2024-01-01T00:00:00Z"),
        ListingSummary(listing_id="C", source_url="https://x/detail/C", updated_at="2024-02-01T00:00:00Z"),
    ]
    res = measure_incremental_efficiency(
        conn,
        run1,
        run2,
        seen_at_run1="2024-01-01T00:00:10Z",
        seen_at_run2="2024-02-01T00:00:10Z",
        fingerprint_ids_run1=["A", "B"],
    )
    assert res["run1_candidates"] == 2
    assert res["run2_candidates"] == 1
    assert 0.49 < res["reduction_ratio"] < 0.51

