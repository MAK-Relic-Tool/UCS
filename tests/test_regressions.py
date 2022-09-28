"""
Tests which ensures releases do not break backwards-compatibility by failing to expose modules/names
"""

import importlib
from typing import List, Iterable, Tuple

import pytest

relic__all__ = [
    "ucs",
]


@pytest.mark.parametrize("submodule", relic__all__)
def test_import_module(submodule: str):
    try:
        importlib.import_module(f"relic.{submodule}")
    except ImportError:
        raise AssertionError(f"{submodule} is no longer exposed!")


ucs__all__ = [
    "UcsDict",
    "UcsFile",
    "lang_code_to_name",
    "walk_ucs",
    "LangEnvironment",
    "get_lang_string_for_file",
    "LANG_CODE_TABLE",
]


def module_imports_helper(submodule: str, all: List[str]) -> Iterable[Tuple[str, str]]:
    return zip([submodule] * len(all), all)


@pytest.mark.parametrize(
    ["submodule", "attribute"],
    [
        *module_imports_helper("ucs", ucs__all__),
    ],
)
def test_module_imports(submodule: str, attribute: str):
    module = importlib.import_module(f"relic.{submodule}")
    _ = getattr(module, attribute)
