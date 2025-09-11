import importlib


def test_import_discovery():
    mod = importlib.import_module("scripts.public_state_jobs.discovery")
    assert hasattr(mod, "__doc__")

