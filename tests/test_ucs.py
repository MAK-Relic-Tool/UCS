import json
from io import StringIO
from pathlib import Path
from typing import List, Iterable, Tuple, Dict, TextIO

import pytest

from relic.ucs import UnicodeStringFile

_path = Path(__file__).parent
try:
    path = _path / "sources.json"
    with path.open() as stream:
        file_sources = json.load(stream)
except IOError as e:
    file_sources = {}

if "dirs" not in file_sources:
    file_sources["dirs"] = []

__implicit_test_data = str(_path / "test_data")

if __implicit_test_data not in file_sources["dirs"]:
    file_sources["dirs"].append(__implicit_test_data)


def ucs_scan_directory(root_dir: str) -> Iterable[str]:
    root_directory = Path(root_dir)
    for path_object in root_directory.glob('**/*.ucs'):
        if path_object.with_suffix(".json").exists():  # ensure expected results file is also present
            yield str(path_object)


ucs_test_files: List[str] = []

for dir in file_sources.get("dirs", []):
    results = ucs_scan_directory(dir)
    ucs_test_files.extend(results)
ucs_test_files.extend(file_sources.get("files", []))

ucs_test_files = list(set(ucs_test_files))  # Get unique paths


class TestLangEnvironment:
    @pytest.fixture(params=ucs_test_files)
    def ucs_file_and_data(self, request) -> Tuple[StringIO, Dict[int, str]]:
        ucs_file:str = request.param
        p = Path(ucs_file)
        p = p.with_suffix('.json')

        with open(p, "r") as data:
            lookup: Dict[str, str] = json.load(data)
            coerced_lookup: Dict[int, str] = {int(key): value for key, value in lookup.items()}

        with open(ucs_file, "r") as ucs_handle:
            text = ucs_handle.read()

        return StringIO(text), coerced_lookup

    def test_ucs(self, ucs_file_and_data: Tuple[TextIO, Dict[int, str]]):
        ucs_stream, ucs_lookup = ucs_file_and_data
        ucs_file = UnicodeStringFile.read_stream(ucs_stream)
        for code, text in ucs_file.items():
            assert code in ucs_lookup
            assert text == ucs_lookup[code]