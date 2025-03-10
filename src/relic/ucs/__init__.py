"""
A library for reading / writing Relic's UCS (Language) files.
"""

from __future__ import annotations

import itertools
import os
import re
from collections import UserDict
from os import PathLike, walk
from os.path import join, splitext, split
from typing import TextIO, Optional, Iterable, Union, Mapping

# UCS probably stands for UnicodeString
#   I personally think that's a horribly misleading name for this file


__version__ = "1.1.0"
StrOrPathLike = Union[str, PathLike[str]]


class UcsDict(UserDict[int, str]):
    """
    A mapping of text-codes to translated strings.
    """

    def write_stream(self, stream: TextIO, ordered: bool = False) -> int:
        """
        Writes the UCS mapping to a text stream.

        :param stream: The output stream.
        :param ordered: If true, the file will list the text-codes from least to greatest.
            Text-codes closer to 0 will be at the start of the file.

        :returns: Number of bytes written.
        """
        written = 0
        items = list(self.data.items())
        if ordered:
            items = sorted(items)
        for key, value in items:
            written += stream.write(f"{key}\t{value}\n")
        return written

    def write(self, file: StrOrPathLike, ordered: bool = False) -> int:
        """
        Writes the UCS mapping to a text file.

        :param file: The output file.
        :param ordered: If true, the file will list the text-codes from least to greatest;
            text-codes closer to 0 will be at the start of the file.

        :returns: Number of bytes written.
        """
        with open(file, "w", encoding="utf-16") as handle:
            return self.write_stream(handle, ordered)


class UcsFile(UcsDict):
    """
    A language file
    """

    @classmethod
    def read(cls, file: StrOrPathLike) -> UcsFile:
        """
        Read a UCS file from the file system.

        :param file: The file path to read from.

        :returns: The UCS file.
        """
        with open(file, "r", encoding="utf-16") as handle:
            return cls.read_stream(handle)

    @classmethod
    def read_stream(cls, stream: TextIO) -> UcsFile:
        """
        Read a UCS file from a stream.

        :param stream: The stream to read from.

        :returns: The UCS file.
        """
        ucs_file = UcsFile()

        prev_num: Optional[int] = None
        # prev_str: str = None
        for line_num, line in enumerate(stream.readlines()):
            safe_line = line.lstrip()
            parts = safe_line.split(maxsplit=1)

            if len(parts) == 0:
                if prev_num is None:
                    raise TypeError(f"Unable to parse line @{line_num}")
                ucs_file[prev_num] += line
                continue
            if len(parts) > 2:
                raise TypeError(f"Unable to parse line @{line_num}")
            # Try parse ucs ID code
            num_str = parts[0]
            line_str = parts[1].rstrip("\n") if len(parts) >= 2 else ""
            try:
                num = int(num_str)
                ucs_file[num] = line_str
                prev_num = num
            except ValueError as ex:  # Not a num; continuation of prev
                if prev_num is None:
                    raise TypeError(f"Unable to parse line @{line_num}") from ex
                ucs_file[prev_num] += safe_line
        return ucs_file


# I could use the 'langcodes' library; but I'm mostly concerned about how Relic's games handle the lang-code naming
#   For example; langcodes might return `Chinese (Simplified)` when I need `Chinese`
#       Rather than rely on a 3rd party library, I'll just allow users to add lang codes manually
#       This way; if a UCS language scheme changes between games, I can then use a custom LANG_CODE_TABLE per game
LANG_CODE_TABLE = {"en": "English"}


def lang_code_to_name(lang_code: str) -> Optional[str]:
    """
    Convert a language code to the name used by the file-system.

    :param lang_code: The language code.

    :returns: The name used to mark UCS files.
    """
    lang_code = lang_code.lower()
    return LANG_CODE_TABLE.get(lang_code)


def walk_ucs(
    folder: StrOrPathLike, lang_code: Optional[str] = None
) -> Iterable[StrOrPathLike]:
    """
    Recursively walks all UCS files with the given language code.

    :param folder: The root folder.
    :param lang_code: The language code to check for.

    :returns: An iterable collection of all UCS file paths.
    """
    walk_result = (
        (file for file in files if splitext(file)[1].lower() == ".ucs")
        for (_, _, files) in walk(folder)
    )
    file_walk_result: Iterable[StrOrPathLike] = itertools.chain.from_iterable(
        walk_result
    )

    def coerce_str(value: StrOrPathLike) -> str:
        if isinstance(value, PathLike):
            return os.fspath(value)
        return value

    if lang_code:
        lang_name = lang_code_to_name(lang_code)
        if lang_name:
            # bug in filter_by_path
            coerced_file_walk_result: Iterable[str] = (
                coerce_str(file) for file in file_walk_result
            )
            coerced_file_walk_result = (
                file for file in coerced_file_walk_result if "Locale" in file
            )
            coerced_file_walk_result = (
                file for file in coerced_file_walk_result if lang_name in file
            )
            file_walk_result = coerced_file_walk_result  # name changed to retype
    return file_walk_result


class LangEnvironment(UcsDict):
    """
    Represents a full translated language, with features to validate text-codes/strings
    """

    def __init__(
        self,
        allow_replacement: bool = False,
        __dict: Optional[Mapping[int, str]] = None,
    ):
        super().__init__(__dict)
        self.allow_replacement = allow_replacement

    def __setitem__(self, k: int, v: str) -> None:
        if self.allow_replacement:
            super(UcsDict, self).__setitem__(k, v)
        else:
            try:
                existing = self.__getitem__(k)
                raise ValueError(
                    f"Key '{k}' exists! Trying to replace '{existing}' with '{v}'!"
                )
            except KeyError:
                super(UcsDict, self).__setitem__(k, v)

    @classmethod
    def load_environment(
        cls,
        folder: StrOrPathLike,
        lang_code: Optional[str] = None,
        allow_replacement: bool = False,
    ) -> LangEnvironment:
        """
        Creates an environment by recursively reading UCS files of the specified langauge from the specified folder.

        :param folder: The root folder to search.
        :param lang_code: The language of files to read.
        :param allow_replacement: If False, the environment will error if a UCS file overwrites a translation.

        :returns: The created Language Environment.
        """
        lang_env = LangEnvironment(allow_replacement=allow_replacement)
        lang_env.read_all(folder, lang_code)
        return lang_env

    def read(self, file: StrOrPathLike) -> None:
        """
        Reads a UCS file into the environment.

        :param file: The UCS file.

        :returns: Nothing, the environment is updated in-place.
        """
        lang_file = UcsFile.read(file)
        self.update(lang_file)

    def read_stream(self, stream: TextIO) -> None:
        """
        Reads a UCS stream into the environment.

        :param stream: The UCS stream.

        :returns: Nothing, the environment is updated in-place.
        """
        lang_file = UcsFile.read_stream(stream)
        self.update(lang_file)

    def read_all(self, folder: StrOrPathLike, lang_code: Optional[str] = None) -> None:
        """
        Read all UCS files for a given language in a folder recursively.

        :param folder: The root folder to search.
        :param lang_code: The language to scan for. If none is given; defaults to English.

        :returns: Nothing, the environment is updated in-place.
        """
        lang_code = lang_code if lang_code is not None else "en"
        for ucs_path in walk_ucs(folder, lang_code):
            self.read(ucs_path)


__safe_regex = re.compile(r"[^A-Za-z0-9_\- .]")
_DEFAULT_REPLACEMENT = ""


def _file_safe_string(word: str, replace: Optional[str] = None) -> str:
    replace = replace or _DEFAULT_REPLACEMENT
    replace = __safe_regex.sub(
        _DEFAULT_REPLACEMENT, replace
    )  # If replace is illegal, use default
    word = __safe_regex.sub(replace, word)
    return word


def get_lang_string_for_file(
    environment: Union[LangEnvironment, UcsFile], file_path: str
) -> str:
    """
    Gets the subtitles for an audio file.

    :param environment: A language environment which maps codes to translations.
    :param file_path: The path of the audio file.

    :returns: The subtitles in the requested language.
    """
    dir_path, f_path = split(file_path)
    file_name, ext = splitext(f_path)
    try:
        # Really arbitrary 'gotcha', some speech files have a random 'b' after the VO Code
        #   This is probably due to a bug in my code, but this will fix the issue
        #       Believe this is fixed in SGA
        # if file_name[-1] == "b":
        #     # raise NotImplementedError(file_name)
        #     file_name = file_name[:-1]
        num = int(file_name)
    except (ValueError, IndexError):
        return file_path

    replacement = environment.get(num)
    if not replacement:
        return file_path

    # The clips are long, and while we could say 'narration' or manually do it
    #   By trimming it to at most
    max_len = 64
    max_trim = 8
    chars = ".!?"  # ;:," # ORDERED SPECIFICALLY FOR THIS
    for char in chars:
        if len(replacement) > max_len:
            replacement = replacement.split(char, 1)[0] + char
        else:
            break
    # Some brute forcing
    if len(replacement) > max_len:
        for i in range(max_trim):
            if replacement[max_len - i - 1] == " ":
                replacement = replacement[: max_len - i] + "..."
    if len(replacement) > max_len:
        replacement = replacement[:max_len] + "..."

    replacement = _file_safe_string(replacement)
    return join(dir_path, replacement + f" ~ Clip {num}" + ext)


__all__ = [
    "UcsDict",
    "UcsFile",
    "lang_code_to_name",
    "walk_ucs",
    "LangEnvironment",
    "get_lang_string_for_file",
    "LANG_CODE_TABLE",
]
