"""Smoke test: the package and every module import cleanly."""
import importlib

import pytest

MODULES = ["bt", "bt.universe", "bt.data", "bt.coverage", "bt.engine", "bt.strategies", "bt.metrics"]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)
