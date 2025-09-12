from pathlib import Path

import types

from scripts.public_state_jobs import cli


class FakeResp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.headers = {}


def test_cli_mocked_crawl(tmp_path, monkeypatch):
    fixtures = Path(__file__).parent.parent / "fixtures"
    list_html = (fixtures / "list_page.html").read_text(encoding="utf-8")
    detail_a = (fixtures / "detail_AAA.html").read_text(encoding="utf-8")
    detail_b = (fixtures / "detail_BBB.html").read_text(encoding="utf-8")

    def fake_get(self, url: str, **kwargs):
        if "page=1" in url:
            return FakeResp(list_html)
        if "/detail/AAA" in url:
            return FakeResp(detail_a)
        if "/detail/BBB" in url:
            return FakeResp(detail_b)
        return FakeResp("", status_code=404)

    # Patch polite fetcher get method
    monkeypatch.setattr(cli.PoliteFetcher, "get", fake_get, raising=True)

    out_dir = tmp_path / "out"
    args = [
        "--base-url", "https://test.local/search",
        "--max-pages", "1",
        "--out-dir", str(out_dir),
        "--no-parquet",
        "--no-csv",
        "--no-robots",
    ]
    rc = cli.main(args)
    assert rc == 0
    # State DB should exist under out_dir
    assert (out_dir / "public_state_jobs.sqlite3").exists()

