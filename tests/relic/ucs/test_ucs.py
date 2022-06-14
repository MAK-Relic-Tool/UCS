import json
from pathlib import Path
from typing import List, Iterable, Tuple, Optional, Union, Dict

import pytest

import relic.sga.v2
from relic import ucs
from relic.sga import Version, MagicWord
from relic.ucs import LangEnvironment, LangFile

_path = Path(__file__).parent
try:
    path = _path / "sources.json"
    with path.open() as stream:
        file_sources = json.load(stream)
except IOError as e:
    file_sources = {}


def ucs_scan_directory(root_dir: str) -> Iterable[str]:
    root_directory = Path(root_dir)
    for path_object in root_directory.glob('**/*.ucs'):
        yield str(path_object)


def sga_scan_directory(root_dir: str, desired_version: Version) -> Iterable[str]:
    root_directory = Path(root_dir)
    for path_object in root_directory.glob('**/*.sga'):
        with path_object.open("rb") as stream:
            if not MagicWord.check_magic_word(stream, advance=True):
                continue
            version = Version.unpack(stream)
            if version != desired_version:
                continue
        yield str(path_object)


def prepare_for_parametrize(files: Iterable[str]) -> Iterable[Tuple[str]]:
    return [(_,) for _ in files]


# Implicit path locations
def _update_implicit_file_sources(src_key: str, sources: Dict = None):
    if sources is None:
        sources = file_sources
    if src_key not in sources:
        sources[src_key] = {}
    if "dirs" not in sources[src_key]:
        sources[src_key]["dirs"] = []
    dirs: List[str] = sources[src_key]["dirs"]
    dirs.append(str(_path / "test_data" / src_key))


def _helper(src_key: str, version: Version, sources: Dict = None):
    if sources is None:
        sources = file_sources
    _update_implicit_file_sources(src_key, sources)
    try:
        local_sources = sources.get(src_key, {})
        files = set()
        for src_dir in local_sources.get("dirs", []):
            for f in sga_scan_directory(src_dir, version):
                files.add(f)
        for src_file in local_sources.get("files", []):
            files.add(src_file)
        return files
        # return prepare_for_parametrize(files)
    except IOError as e:
        return tuple()


v2_en_env = LangEnvironment.load_environment(file_sources.get("v2", {}).get("LangEnv"))
v2_archives = _helper("SGA", relic.sga.v2.version, file_sources.get("v2", {}))


class TestLangEnvironment:
    @pytest.mark.parametrize(["folder"], [*prepare_for_parametrize(file_sources.get("LangEnv", []))])
    def test_load_env(self, folder: str, lang_code: Optional[str] = None, allow_replacement: bool = False):
        # Not the best test; but so long as no errors are occurring; we know it's somewhat working
        _ = LangEnvironment.load_environment(folder, lang_code, allow_replacement)

    @pytest.mark.parametrize(["env", "archive_path"], [*zip([v2_en_env] * len(v2_archives), v2_archives)])
    def test_get_lang_string_for_file(self, env: Union[LangEnvironment, LangFile], archive_path: str):
        # Not the best test; but so long as no errors are occurring; we know it's somewhat working
        with open(archive_path, "rb") as stream:
            archive = relic.sga.v2.ArchiveIO.read(stream, lazy=True)
            for _, _, files in archive.walk():
                for file in files:
                    name: str = file.name
                    if name.endswith(".fda"):  # audio file
                        _ = ucs.get_lang_string_for_file(env, name)
