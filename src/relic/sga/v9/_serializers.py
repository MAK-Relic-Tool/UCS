"""
Binary Serializers for Relic's SGA-V9
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import BinaryIO

from serialization_tools.structx import Struct

from relic.errors import MismatchError
from relic.sga import _abc, _serializers as _s
from relic.sga._abc import ArchivePtrs
from relic.sga._core import StorageType, VerificationType, Version, MagicWord
from relic.sga._serializers import read_toc, load_lazy_data
from relic.sga.errors import VersionMismatchError
from relic.sga.protocols import StreamSerializer
from relic.sga.v9 import core

folder_layout = Struct("<5I")
folder_serializer = _s.FolderDefSerializer(folder_layout)

drive_layout = Struct("<64s 64s 5I")
drive_serializer = _s.DriveDefSerializer(drive_layout)

file_layout = Struct("<2I Q 3I 2B I")


class FileDefSerializer(StreamSerializer[core.FileDef]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> core.FileDef:
        name_rel_pos, \
        hash_pos, \
        data_rel_pos, \
        length, \
        store_length, \
        modified_seconds, \
        verification_type_val, \
        storage_type_val, \
        crc = self.layout.unpack_stream(stream)

        modified = datetime.fromtimestamp(modified_seconds, timezone.utc)
        storage_type: StorageType = StorageType(storage_type_val)
        verification_type: VerificationType = VerificationType(verification_type_val)

        return core.FileDef(name_rel_pos, data_rel_pos, length, store_length, storage_type, modified, verification_type, crc, hash_pos)

    def pack(self, stream: BinaryIO, value: core.FileDef) -> int:
        modified: int = int(value.modified.timestamp())
        storage_type = value.storage_type.value  # convert enum to value
        verification_type = value.verification.value  # convert enum to value
        args = value.name_pos, value.hash_pos, value.data_pos, value.length_on_disk, value.length_in_archive, storage_type, modified, verification_type, value.crc
        return self.layout.pack_stream(stream, *args)


file_serializer = FileDefSerializer(file_layout)
toc_layout = Struct("<8I")
toc_header_serializer = _s.TocHeaderSerializer(toc_layout)


class APISerializers(_abc.ArchiveSerializer):
    def read(self, stream: BinaryIO, lazy: bool = False, decompress: bool = True) -> core.Archive:
        MagicWord.read_magic_word(stream)
        version: Version = Version.unpack(stream)
        if version != self.version:
            raise VersionMismatchError(version, self.version)

        layout:Struct = self.layout
        encoded_name: bytes
        encoded_name, header_pos, header_size, data_pos, data_size, rsv_1, sha_256 = layout.unpack_stream(stream)
        if rsv_1 != 1:
            raise MismatchError("Reserved Field", rsv_1, 1)
        # header_pos = stream.tell()
        stream.seek(header_pos)
        ptrs = ArchivePtrs(header_pos,header_size,data_pos,data_size)
        toc_header = self.TocHeader.unpack(stream)
        unk_a, unk_b, block_size = self.metadata_layout.unpack_stream(stream)
        drives, files = read_toc(
            stream=stream,
            toc_header=toc_header,
            ptrs=ptrs,
            drive_def=self.DriveDef,
            file_def=self.FileDef,
            folder_def=self.FolderDef,
            decompress=decompress,
            build_file_meta=lambda _: None,  # V2 has no metadata
            name_toc_is_count=True
        )
        # TODO perform a header check

        if not lazy:
            load_lazy_data(files)

        name: str = encoded_name.rstrip(b"").decode("utf-16-le")
        metadata = core.ArchiveMetadata(sha_256, unk_a, unk_b, block_size)

        return core.Archive(name, metadata, drives)

    def write(self, stream: BinaryIO, archive: core.Archive) -> int:
        raise NotImplementedError

    def __init__(self) -> None:
        self.DriveDef = drive_serializer
        self.FolderDef = folder_serializer
        self.FileDef = file_serializer
        self.TocHeader = toc_header_serializer
        self.version: Version = core.version
        self.layout = Struct("<128s QIQQ I 256s")
        self.metadata_layout = Struct("<3I")
