import importlib


def test_import_org_match():
    mod = importlib.import_module("scripts.public_state_jobs.org_match")
    assert hasattr(mod, "__doc__")

