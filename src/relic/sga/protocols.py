from __future__ import annotations

from pathlib import PurePath
from typing import TypeVar, Protocol, List, Optional, Iterable, BinaryIO, runtime_checkable, Sequence, Tuple

TParent = TypeVar("TParent")
TParent_co = TypeVar("TParent_co", covariant=True)
TArchive = TypeVar("TArchive")
TFolder = TypeVar("TFolder")
TFolder_co = TypeVar("TFolder_co", covariant=True)
TFile = TypeVar("TFile")
TFile_co = TypeVar("TFile_co", covariant=True)
T = TypeVar("T")


@runtime_checkable
class StreamSerializer(Protocol[T]):
    """Serializes the Type to/from a binary stream."""
    def unpack(self, stream: BinaryIO) -> T:
        raise NotImplementedError

    def pack(self, stream: BinaryIO, value: T) -> int:
        raise NotImplementedError


@runtime_checkable
class IOPathable(Protocol):
    # pylint: disable=too-few-public-methods
    @property
    def path(self) -> PurePath:
        raise NotImplementedError


class IOChild(Protocol[TParent]):
    # pylint: disable=too-few-public-methods
    parent: Optional[TParent]


class IOContainer(Protocol[TFolder, TFile]):
    # pylint: disable=too-few-public-methods
    sub_folders: List[TFolder]
    files: List[TFile]


IOWalk = Iterable[Tuple[TParent_co, Sequence[TFolder_co], Sequence[TFile_co]]]


class IOWalkable(Protocol[TParent_co, TFolder_co, TFile_co]):
    # pylint: disable=too-few-public-methods
    def walk(self) -> IOWalk[TParent_co, TFolder_co, TFile_co]:
        raise NotImplementedError


class ArchiveIO(Protocol[TArchive]):
    def read(self, stream: BinaryIO, lazy: bool = False, decompress: bool = True) -> TArchive:
        raise NotImplementedError

    def write(self, stream: BinaryIO, archive: TArchive) -> int:
        raise NotImplementedError
