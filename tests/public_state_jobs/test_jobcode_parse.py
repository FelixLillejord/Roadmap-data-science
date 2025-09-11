import importlib


def test_import_jobcode_parse():
    mod = importlib.import_module("scripts.public_state_jobs.jobcode_parse")
    assert hasattr(mod, "__doc__")

