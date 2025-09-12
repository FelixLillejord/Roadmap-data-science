from scripts.public_state_jobs.jobcode_parse import extract_job_codes, extract_code_titles


def test_extract_job_codes_basic_and_distinct():
    text = "Stillingskode 1234 – Tittel; Kode 5678 – Tittel; Kode 1234"
    codes = extract_job_codes(text)
    assert codes == ["1234", "5678"]


def test_extract_code_titles_pairs():
    text = "Stillingskode 1408 – Førstekonsulent\nKode 1364 – Senioringeniør"
    pairs = dict(extract_code_titles(text))
    assert pairs["1408"].lower().startswith("første")
    assert pairs["1364"].lower().startswith("senior")
