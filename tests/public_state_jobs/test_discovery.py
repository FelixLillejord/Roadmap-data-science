from scripts.public_state_jobs.discovery import (
    SearchParams,
    build_search_url,
    paginate_search,
    derive_listing_id,
    normalize_source_url,
)


def test_build_search_url_basic():
    url = build_search_url(params=SearchParams(page=2, open_only=True))
    assert "page=2" in url
    assert "open_only=true" in url


def test_paginate_search_bounded():
    seen = []

    def fake_fetch(url: str) -> str:
        return f"<html>{url}</html>"

    for page, url, html in paginate_search(fake_fetch, params=SearchParams(), max_pages=3):
        seen.append(page)
        assert f"page={page}" in url
        assert url in html

    assert seen == [1, 2, 3]


def test_paginate_search_has_next():
    def fake_fetch(url: str) -> str:
        # Echo back the url so we can inspect it if needed
        return url

    def has_next(html: str, page: int) -> bool:
        # Stop after page 3
        return page < 3

    pages = [p for p, _u, _h in ((p, u, h) for p, u, h in paginate_search(fake_fetch, has_next=has_next))]
    assert pages == [1, 2, 3]


def test_derive_listing_id_precedence_candidate():
    listing_id, prov = derive_listing_id("https://example.com/detail/xyz", id_candidates=("CAND123",))
    assert listing_id == "CAND123"
    assert prov == "candidate"


def test_derive_listing_id_uuid_preferred():
    url = "https://example.com/jobs/4F8C1B2A-3d4e-5f60-a1b2-334455667788"
    listing_id, prov = derive_listing_id(url)
    assert listing_id == "4f8c1b2a-3d4e-5f60-a1b2-334455667788"
    assert prov == "url_uuid"


def test_derive_listing_id_numeric_path():
    url = "https://example.com/jobs/department/1234567/details"
    listing_id, prov = derive_listing_id(url)
    assert listing_id == "1234567"
    assert prov == "url_numeric"


def test_derive_listing_id_query_param():
    url = "https://example.com/detail?jobId=ABC999"
    listing_id, prov = derive_listing_id(url)
    assert listing_id == "ABC999"
    assert prov == "url_query"


def test_normalize_source_url_and_hash_stability():
    base = "https://example.com/detail/42"
    url_a = base + "?b=2&a=1&utm_source=google#section"
    url_b = base + "?a=1&b=2&gclid=123"

    norm_a = normalize_source_url(url_a)
    norm_b = normalize_source_url(url_b)
    assert norm_a == norm_b

    id_a, prov_a = derive_listing_id(url_a)
    id_b, prov_b = derive_listing_id(url_b)
    assert id_a == id_b
    assert prov_a == prov_b == "sha1_url"
