import importlib


def test_import_detail_parse():
    mod = importlib.import_module("scripts.public_state_jobs.detail_parse")
    assert hasattr(mod, "__doc__")

