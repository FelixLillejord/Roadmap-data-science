from scripts.public_state_jobs.org_match import (
    match_org,
    normalize_org_text,
)


def test_normalize_removes_accents_punct_and_collapses_ws():
    s = "  Førsvar-etaten!!  "
    assert normalize_org_text(s) == "forsvar etaten"


def test_employer_synonyms_match_pst_and_nsm():
    tag, prov = match_org("Politiets sikkerhetstjeneste", None)
    assert tag == "pst" and prov == "employer_synonym"

    tag, prov = match_org("Nasjonal sikkerhetsmyndighet", None)
    assert tag == "nsm" and prov == "employer_synonym"


def test_employer_prefix_forsvar():
    tag, prov = match_org("Forsvaret", None)
    assert tag == "forsvar" and prov == "employer_prefix"


def test_employer_exact_tags():
    assert match_org("PST", None) == ("pst", "employer_exact")
    assert match_org("NSM", None) == ("nsm", "employer_exact")
    assert match_org("forsvar", None) == ("forsvar", "employer_exact")


def test_title_fallback_requires_state_sector_and_only_forsvar():
    # With state sector applied, title token prefix triggers Forsvar
    tag, prov = match_org("", "Seniorrådgiver i Forsvarssektoren", state_sector_applied=True)
    assert tag == "forsvar" and prov == "title_prefix_forsvar"

    # Without state sector flag, no fallback
    tag, prov = match_org("", "Forsvarssektoren", state_sector_applied=False)
    assert tag is None and prov == "none"


def test_fuzzy_threshold_allows_close_variants():
    # Slight misspelling should match PST with fuzzy threshold
    tag, prov = match_org("Politiets Sikkerhetstjenst", None, fuzzy_threshold=0.8)
    assert tag == "pst" and prov.startswith("employer_fuzzy_")

    # And for NSM
    tag, prov = match_org("Nasjonal sikkerhetsmyndghet", None, fuzzy_threshold=0.8)
    assert tag == "nsm" and prov.startswith("employer_fuzzy_")


def test_no_match_returns_none():
    tag, prov = match_org("Ukjent Direktorat", "Random title")
    assert tag is None and prov == "none"
