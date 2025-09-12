from scripts.public_state_jobs.detail_parse import (
    parse_detail_fields,
    parse_job_codes_and_salaries,
)


def test_detail_parse_forsvar_example():
    html = """
    <html>
      <body>
        <h1 class="job-title">Seniorrådgiver – Analyse</h1>
        <div class="employer-name">Forsvaret</div>
        <div class="job-locations">Oslo, Bergen</div>
        <div class="employment-type">Fast</div>
        <div class="employment-extent">100%</div>
        <div class="salary">Lønn: kr 600 000 – 750 000 per år</div>
        <div class="job-codes">
          <p>Stillingskode 1234 – Rådgiver</p>
          <p>Kode 5678 – Seniorrådgiver</p>
        </div>
        <time class="published">2024-05-01T00:00:00Z</time>
        <time class="updated">2024-05-02T00:00:00Z</time>
        <time class="deadline">2024-06-01T00:00:00Z</time>
      </body>
    </html>
    """
    fields = parse_detail_fields(html, source_url="https://example.com/forsvar/123")
    assert fields["title"].startswith("Seniorrådgiver")
    assert fields["employer_normalized"] == "forsvaret"
    assert fields["locations"] == ["Oslo", "Bergen"]
    assert fields["published_at"] == "2024-05-01T00:00:00Z"
    assert fields["source_url"] == "https://example.com/forsvar/123"

    rows = parse_job_codes_and_salaries(html)
    codes = {r["job_code"] for r in rows}
    assert codes == {"1234", "5678"}
    # Salary range applied to both codes
    for r in rows:
        assert r["salary_min"] == 600000
        assert r["salary_max"] == 750000
        assert r["is_shared_salary"] is True


def test_detail_parse_pst_example():
    html = """
    <html>
      <body>
        <h1 class="job-title">Analytiker</h1>
        <div class="employer-name">Politiets sikkerhetstjeneste</div>
        <div class="job-locations">Oslo</div>
        <div class="salary">Lønn etter avtale</div>
        <div class="job-codes">
          <p>Stillingskode 1408 – Førstekonsulent</p>
        </div>
      </body>
    </html>
    """
    fields = parse_detail_fields(html, source_url="https://example.com/pst/abc")
    assert fields["employer_normalized"] == "politiets sikkerhetstjeneste"

    rows = parse_job_codes_and_salaries(html)
    assert rows and rows[0]["job_code"] == "1408"
    assert rows[0]["salary_min"] is None and rows[0]["salary_max"] is None


def test_detail_parse_nsm_example_single_value_salary():
    html = """
    <html>
      <body>
        <h1 class="job-title">Rådgiver – IKT sikkerhet</h1>
        <div class="employer-name">Nasjonal sikkerhetsmyndighet</div>
        <div class="salary">Lønn: kr 650.000</div>
        <div class="job-codes">
          <p>kode 1364 – Senioringeniør</p>
        </div>
      </body>
    </html>
    """
    rows = parse_job_codes_and_salaries(html)
    assert rows[0]["job_code"] == "1364"
    assert rows[0]["salary_min"] == 650000 and rows[0]["salary_max"] == 650000


def test_detail_block_salary_not_shared():
    html = """
    <html>
      <body>
        <div class="job-codes">
          <p>kode 1111 – Konsulent – Lønn: kr 500 000 – 600 000</p>
        </div>
      </body>
    </html>
    """
    rows = parse_job_codes_and_salaries(html)
    assert rows == [
        {
            "job_code": "1111",
            "job_title": "Konsulent – Lønn: kr 500 000 – 600 000",
            "salary_min": 500000,
            "salary_max": 600000,
            "salary_text": "kode 1111 – Konsulent – Lønn: kr 500 000 – 600 000",
            "is_shared_salary": False,
        }
    ]
