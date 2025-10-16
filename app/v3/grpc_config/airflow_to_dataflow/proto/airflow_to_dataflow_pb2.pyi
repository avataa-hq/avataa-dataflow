from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RequestGetDestinationData(_message.Message):
    __slots__ = ["destination_id"]
    DESTINATION_ID_FIELD_NUMBER: _ClassVar[int]
    destination_id: int
    def __init__(self, destination_id: _Optional[int] = ...) -> None: ...

class RequestGetSourceConfiguration(_message.Message):
    __slots__ = ["source_id"]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    source_id: int
    def __init__(self, source_id: _Optional[int] = ...) -> None: ...

class ResponseGetDestinationData(_message.Message):
    __slots__ = ["destination_data"]
    DESTINATION_DATA_FIELD_NUMBER: _ClassVar[int]
    destination_data: str
    def __init__(self, destination_data: _Optional[str] = ...) -> None: ...

class ResponseGetSourceConfiguration(_message.Message):
    __slots__ = ["source_data"]
    SOURCE_DATA_FIELD_NUMBER: _ClassVar[int]
    source_data: str
    def __init__(self, source_data: _Optional[str] = ...) -> None: ...
