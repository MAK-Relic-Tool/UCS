from __future__ import annotations

from datetime import datetime, timezone
from typing import BinaryIO, ClassVar, Optional

from serialization_tools.structx import Struct

from relic.sga._abc import ArchivePtrs
from relic.sga._serializers import read_toc, load_lazy_data

import relic.sga._serializers
from relic.sga import _abc, _serializers as _s
from relic.sga.errors import VersionMismatchError
from relic.errors import MismatchError
from relic.sga.protocols import StreamSerializer
from relic.sga._core import StorageType, VerificationType, MagicWord, Version
from relic.sga.v5 import core

folder_layout = Struct("<I 4H")
folder_serializer = _s.FolderDefSerializer(folder_layout)

drive_layout = Struct("<64s 64s 5H")
drive_serializer = _s.DriveDefSerializer(drive_layout)

file_layout = Struct("<5I 2B")


class FileDefSerializer(StreamSerializer[core.FileDef]):
    def __init__(self, layout: Struct):
        self.layout = layout

    def unpack(self, stream: BinaryIO) -> core.FileDef:
        name_rel_pos, data_rel_pos, length, store_length, modified_seconds, verification_type_val, storage_type_val = self.layout.unpack_stream(stream)

        modified = datetime.fromtimestamp(modified_seconds, timezone.utc)
        storage_type: StorageType = StorageType(storage_type_val)
        verification_type: VerificationType = VerificationType(verification_type_val)

        return core.FileDef(name_rel_pos, data_rel_pos, length, store_length, storage_type, modified, verification_type)

    def pack(self, stream: BinaryIO, value: core.FileDef) -> int:
        modified: int = int(value.modified.timestamp())
        storage_type = value.storage_type.value  # convert enum to value
        verification_type = value.verification.value  # convert enum to value
        args = value.name_pos, value.data_pos, value.length_on_disk, value.length_in_archive, storage_type, modified, verification_type
        return self.layout.pack_stream(stream, *args)


file_serializer = FileDefSerializer(file_layout)
toc_layout = Struct("<IH IH IH IH")
toc_header_serializer = _s.TocHeaderSerializer(toc_layout)


class APISerializers(_abc.ArchiveSerializer):
    FILE_MD5_EIGEN: ClassVar = b"E01519D6-2DB7-4640-AF54-0A23319C56C3"
    HEADER_MD5_EIGEN: ClassVar = b"DFC9AF62-FC1B-4180-BC27-11CCE87D3EFF"

    def read(self, stream: BinaryIO, lazy: bool = False, decompress: bool = True) -> core.Archive:
        MagicWord.read_magic_word(stream)
        version = Version.unpack(stream)
        if version != self.version:
            raise VersionMismatchError(version, self.version)

        encoded_name: bytes
        file_md5, encoded_name, header_md5, header_size, data_pos, header_pos, rsv_1, rsv_0, unk_a = self.layout.unpack_stream(stream)
        if (rsv_1, rsv_0) != (1, 0):
            raise MismatchError("Reserved Field", (rsv_1, rsv_0), (1, 0))
        ptrs = ArchivePtrs(header_pos,header_size,data_pos)
        # header_pos = stream.tell()
        stream.seek(header_pos)
        toc_header = self.TocHeader.unpack(stream)
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

        if not lazy:
            load_lazy_data(files)

        name: str = encoded_name.rstrip(b"").decode("utf-16-le")
        file_md5_helper = relic.sga._serializers.Md5ChecksumHelper(file_md5, stream, header_pos, eigen=self.FILE_MD5_EIGEN)
        header_md5_helper = relic.sga._serializers.Md5ChecksumHelper(header_md5, stream, header_pos, header_size, eigen=self.FILE_MD5_EIGEN)
        metadata = core.ArchiveMetadata(file_md5_helper, header_md5_helper, unk_a)

        return core.Archive(name, metadata, drives)

    def write(self, stream: BinaryIO, archive: core.Archive) -> int:
        raise NotImplementedError

    def __init__(self) -> None:
        self.DriveDef = drive_serializer
        self.FolderDef = folder_serializer
        self.FileDef = file_serializer
        self.TocHeader = toc_header_serializer
        self.version = core.version
        self.layout = Struct("<16s 128s 16s 6I")
