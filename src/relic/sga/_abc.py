from __future__ import annotations

import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from typing import List, Optional, Tuple, BinaryIO, Generic, TypeVar, Sequence, Any, Union, Generator

from relic.sga import protocols as p
from relic.sga._core import StorageType
from relic.sga.errors import DecompressedSizeMismatch
from relic.sga.protocols import IONode, IOPathable


def _build_io_path(name: str, parent: Optional[Any]) -> PurePath:
    if parent is not None and isinstance(parent, p.IOPathable):
        parent_path: PurePath = parent.path
        return parent_path / name
    return PurePath(name)


TMetadata = TypeVar("TMetadata")
TFileMetadata = TypeVar("TFileMetadata")


@dataclass
class FileLazyInfo:
    jump_to: int
    packed_size: int
    unpacked_size: int
    stream: BinaryIO
    decompress: bool

    def read(self, decompress: Optional[bool] = None) -> bytes:
        decompress = self.decompress if decompress is None else decompress
        jump_back = self.stream.tell()
        self.stream.seek(self.jump_to)
        buffer = self.stream.read(self.packed_size)
        if decompress and self.packed_size != self.unpacked_size:
            buffer = zlib.decompress(buffer)
            if len(buffer) != self.unpacked_size:
                raise DecompressedSizeMismatch(len(buffer), self.unpacked_size)
        self.stream.seek(jump_back)
        return buffer


@dataclass
class DriveDef:
    alias: str
    name: str
    root_folder: int
    folder_range: Tuple[int, int]
    file_range: Tuple[int, int]


@dataclass
class FolderDef:
    name_pos: int
    folder_range: Tuple[int, int]
    file_range: Tuple[int, int]


@dataclass
class FileDefABC:
    name_pos: int
    data_pos: int
    length_on_disk: int
    length_in_archive: int
    storage_type: StorageType


_WalkParent = Union['Drive[TFileMetadata]', 'Folder[TFileMetadata]']


@dataclass
class Drive(Generic[TFileMetadata]):
    alias: str
    name: str
    sub_folders: List[Folder[TFileMetadata]]
    files: List[File[TFileMetadata]]
    parent: None = None
    __ignore__ = ["parent"]

    @property
    def path(self) -> PurePath:
        return _build_io_path(f"{self.alias}:", None)

    def walk(self) -> p.IOWalk[_WalkParent, Folder[TFileMetadata], File[TFileMetadata]]:
        yield self, self.sub_folders, self.files
        for folder in self.sub_folders:
            for inner_walk in folder.walk():
                yield inner_walk


@dataclass
class Folder(Generic[TFileMetadata]):
    name: str
    sub_folders: List[Folder[TFileMetadata]]
    files: List[File[TFileMetadata]]
    parent: Optional[_WalkParent] = None

    @property
    def path(self) -> PurePath:
        return _build_io_path(self.name, self.parent)

    def walk(self) -> p.IOWalk[_WalkParent, Folder[TFileMetadata], File[TFileMetadata]]:
        yield self, self.sub_folders, self.files
        for folder in self.sub_folders:
            for inner_walk in folder.walk():
                yield inner_walk


@dataclass
class File(Generic[TFileMetadata]):
    name: str
    _data: Optional[bytes]
    storage_type: StorageType
    _is_compressed: bool
    metadata: TFileMetadata
    parent: Optional[_WalkParent] = None
    _lazy_info: Optional[FileLazyInfo] = None

    @property
    def data(self) -> bytes:
        if self._data is None:
            if self._lazy_info is None:
                raise TypeError("Data was not loaded!")
            else:
                self._data = self._lazy_info.read()
                self._lazy_info = None
        return self._data

    @data.setter
    def data(self, value: bytes) -> None:
        self._data = value

    @contextmanager
    def open(self, read_only: bool = True) -> Generator[BinaryIO, None, None]:
        data = self.data
        with BytesIO(data) as stream:
            yield stream
            if not read_only:
                stream.seek(0)
                self.data = stream.read()

    @property
    def is_compressed(self) -> bool:
        return self._is_compressed

    def compress(self) -> None:
        if self.data is None:
            raise TypeError("Data was not loaded!")
        if not self._is_compressed:
            self.data = zlib.compress(self.data)
            self._is_compressed = True

    def decompress(self) -> None:
        if self._is_compressed:
            self.data = zlib.decompress(self.data)
            self._is_compressed = False

    @property
    def path(self) -> PurePath:
        return _build_io_path(self.name, self.parent)


# IOParent =


@dataclass
class Archive(Generic[TMetadata, TFileMetadata]):
    name: str
    metadata: TMetadata
    drives: Sequence[Drive[TFileMetadata]]

    def walk(self) -> p.IOWalk:
        for drive in self.drives:
            for inner_walk in drive.walk():
                yield inner_walk


TArchive = TypeVar("TArchive", bound=Archive)


class ArchiveSerializer(p.ArchiveIO[TArchive]):
    def read(self, stream: BinaryIO, lazy: bool = False, decompress: bool = True) -> TArchive:
        raise NotImplementedError

    def write(self, stream: BinaryIO, archive: TArchive) -> int:
        raise NotImplementedError


@dataclass
class TocHeader:
    drive_info: Tuple[int, int]
    folder_info: Tuple[int, int]
    file_info: Tuple[int, int]
    name_info: Tuple[int, int]


@dataclass
class ArchivePtrs:
    header_pos: int
    header_size: int
    data_pos: int
    data_size: Optional[int] = None
