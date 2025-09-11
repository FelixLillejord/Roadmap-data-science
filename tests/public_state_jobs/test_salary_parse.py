import importlib


def test_import_salary_parse():
    mod = importlib.import_module("scripts.public_state_jobs.salary_parse")
    assert hasattr(mod, "__doc__")

