from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RequestCheckDestination(_message.Message):
    __slots__ = ["con_type", "destination_id"]
    CON_TYPE_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_ID_FIELD_NUMBER: _ClassVar[int]
    con_type: str
    destination_id: int
    def __init__(self, destination_id: _Optional[int] = ..., con_type: _Optional[str] = ...) -> None: ...

class RequestSourceConData(_message.Message):
    __slots__ = ["sources"]
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    sources: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, sources: _Optional[_Iterable[int]] = ...) -> None: ...

class ResponseCheckDestination(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class ResponseSourceConData(_message.Message):
    __slots__ = ["con_data"]
    class ConDataEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: str
        def __init__(self, key: _Optional[int] = ..., value: _Optional[str] = ...) -> None: ...
    CON_DATA_FIELD_NUMBER: _ClassVar[int]
    con_data: _containers.ScalarMap[int, str]
    def __init__(self, con_data: _Optional[_Mapping[int, str]] = ...) -> None: ...
