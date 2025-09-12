from scripts.public_state_jobs.models import explode_listing


def test_explode_listing_maps_fields_and_salary():
    listing_id = "L1"
    source_url = "https://example.com/detail/L1"
    fields = {
        "employer_normalized": "forsvaret",
        "published_at": "2024-05-01T00:00:00Z",
        "updated_at": "2024-05-02T00:00:00Z",
        "apply_deadline": "2024-06-01T00:00:00Z",
    }
    code_rows = [
        {"job_code": "1234", "job_title": "Rådgiver", "salary_min": 600000, "salary_max": 750000, "salary_text": "kr 600 000 – 750 000", "is_shared_salary": True},
        {"job_code": "5678", "job_title": "Seniorrådgiver", "salary_min": 600000, "salary_max": 750000, "salary_text": "kr 600 000 – 750 000", "is_shared_salary": True},
    ]

    rows = explode_listing(listing_id=listing_id, source_url=source_url, fields=fields, code_rows=code_rows, scraped_at="2024-05-03T00:00:00Z")
    assert len(rows) == 2
    one = rows[0].to_dict()
    assert one["listing_id"] == "L1"
    assert one["source_url"] == source_url
    assert one["employer_normalized"] == "forsvaret"
    assert one["salary_min"] == 600000 and one["is_shared_salary"] is True
    assert one["published_at"] == fields["published_at"]

