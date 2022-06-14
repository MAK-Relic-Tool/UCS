from __future__ import annotations

from contextlib import contextmanager
from pathlib import PurePath
from typing import TypeVar, Protocol, List, Optional, Iterable, BinaryIO, runtime_checkable, Sequence, Tuple, Generator

from relic.sga._core import StorageType

TMetadata = TypeVar("TMetadata")
TParent = TypeVar("TParent")
TParent_co = TypeVar("TParent_co", covariant=True)
TArchive = TypeVar("TArchive")
TArchive_co = TypeVar("TArchive_co", covariant=True)
TDrive = TypeVar("TDrive")
TDrive_co = TypeVar("TDrive_co", covariant=True)
TFolder = TypeVar("TFolder")
TFolder_co = TypeVar("TFolder_co", covariant=True)
TFile = TypeVar("TFile")
TFile_co = TypeVar("TFile_co", covariant=True)
T = TypeVar("T")


@runtime_checkable
class StreamSerializer(Protocol[T]):
    def unpack(self, stream: BinaryIO) -> T:
        raise NotImplementedError

    def pack(self, stream: BinaryIO, value: T) -> int:
        raise NotImplementedError


@runtime_checkable
class IOPathable(Protocol):
    @property
    def path(self) -> PurePath:
        raise NotImplementedError


class IONode(Protocol[TParent]):
    parent: Optional[TParent]


class IOContainer(Protocol[TFolder, TFile]):
    sub_folders: List[TFolder]
    files: List[TFile]


IOWalk = Iterable[Tuple[TParent_co, Sequence[TFolder_co], Sequence[TFile_co]]]


class IOWalkable(Protocol[TParent_co, TFolder_co, TFile_co]):
    def walk(self) -> IOWalk[TParent_co, TFolder_co, TFile_co]:
        raise NotImplementedError


class _IOFile(IOPathable, IONode[TParent], Protocol[TParent]):
    ...


class _IOFolder(IOWalkable[TParent_co, TFolder_co, TFile_co], IOPathable, IONode[TParent], IOContainer[TFolder, TFile], Protocol[TParent, TParent_co, TFolder, TFolder_co, TFile, TFile_co]):
    ...


class ArchiveIO(Protocol[TArchive]):
    def read(self, stream: BinaryIO, lazy: bool = False, decompress: bool = True) -> TArchive:
        raise NotImplementedError

    def write(self, stream: BinaryIO, archive: TArchive) -> int:
        raise NotImplementedError
