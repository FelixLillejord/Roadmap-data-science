from scripts.public_state_jobs.models import (
    ExplodedJobRow,
    to_exploded_dataframe,
    EXPLODED_COLUMNS,
    EXPLODED_DTYPES,
)


def test_to_exploded_dataframe_dtypes_and_order_consistency():
    rows_run1 = [
        ExplodedJobRow(
            listing_id="L1",
            job_code="1234",
            job_title=None,
            employer_normalized="forsvaret",
            salary_min=600000,
            salary_max=750000,
            salary_text="600000-750000",
            is_shared_salary=True,
            published_at=None,
            updated_at=None,
            apply_deadline=None,
            source_url="https://example.com/L1",
        )
    ]
    df1 = to_exploded_dataframe(rows_run1)

    # Second run with different missingness and order
    rows_run2 = [
        {
            "job_code": "5678",
            "listing_id": "L2",
            "employer_normalized": "pst",
            "salary_min": None,
            "salary_max": None,
            "salary_text": None,
            "is_shared_salary": False,
            "source_url": "https://example.com/L2",
        }
    ]
    df2 = to_exploded_dataframe(rows_run2)

    # Check column order equality to schema
    assert list(df1.columns) == EXPLODED_COLUMNS
    assert list(df2.columns) == EXPLODED_COLUMNS

    # Check dtypes match expected pandas dtypes
    assert [str(t) for t in df1.dtypes] == [EXPLODED_DTYPES[c] for c in EXPLODED_COLUMNS]
    assert [str(t) for t in df2.dtypes] == [EXPLODED_DTYPES[c] for c in EXPLODED_COLUMNS]

