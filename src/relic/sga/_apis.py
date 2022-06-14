from typing import List, Dict, BinaryIO, Any

from relic.sga import v2, v5, v7, v9, protocols
from relic.sga._core import Version, MagicWord

# _APIS: List[protocols.API] = [v2.API, v5.API, v7.API, v9.API]
# apis: Dict[Version, protocols.API] = {api.version: api for api in _APIS}
# _APIS: List = [None, v5.API, v7.API, v9.API]
apis: Dict[Version, Any] = {} # {api.version: api for api in _APIS}


def read(stream: BinaryIO, lazy: bool = False, decompress: bool = True, api_lookup: Dict[Version, Any] = None) -> Any:#protocols.Archive:
    api_lookup = api_lookup if api_lookup is not None else apis
    MagicWord.read_magic_word(stream)
    version = Version.unpack(stream)
    api = api_lookup[version]
    return api.read(stream, lazy, decompress)
