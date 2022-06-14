"""
Relic's V9 Specification for SGA files.

Used in Age of Empires 4.
"""

from relic.sga import _abc
from relic.sga.v9._serializers import APISerializers
from relic.sga.v9.core import Archive, Drive, Folder, File, ArchiveMetadata, version


# def _create_api():
#     raise NotImplementedError
    # serializer = APISerializers()
    # api = _abc.API(version, Archive, Drive, Folder, File, serializer)
    # return api


API = None#_create_api()


__all__ = [
    "Archive",
    "Drive",
    "Folder",
    "File",
    "API",
    "version",
    "ArchiveMetadata"
]
