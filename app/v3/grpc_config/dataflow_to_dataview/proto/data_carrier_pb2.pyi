from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ConfigRequest(_message.Message):
    __slots__ = ["columns", "source_id"]
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    columns: _containers.RepeatedScalarFieldContainer[str]
    source_id: int
    def __init__(self, source_id: _Optional[int] = ..., columns: _Optional[_Iterable[str]] = ...) -> None: ...

class ConfigWithTypesRequest(_message.Message):
    __slots__ = ["columns", "source_id"]
    class ColumnsEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    COLUMNS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    columns: _containers.ScalarMap[str, str]
    source_id: int
    def __init__(self, source_id: _Optional[int] = ..., columns: _Optional[_Mapping[str, str]] = ...) -> None: ...

class DataRequest(_message.Message):
    __slots__ = ["count", "data_row", "source_id"]
    class DataRowEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    COUNT_FIELD_NUMBER: _ClassVar[int]
    DATA_ROW_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    count: int
    data_row: _containers.ScalarMap[str, str]
    source_id: int
    def __init__(self, source_id: _Optional[int] = ..., count: _Optional[int] = ..., data_row: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GroupDeleteRequest(_message.Message):
    __slots__ = ["group_id"]
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    group_id: int
    def __init__(self, group_id: _Optional[int] = ...) -> None: ...

class GroupRequest(_message.Message):
    __slots__ = ["group_id", "name"]
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    group_id: int
    name: str
    def __init__(self, group_id: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...

class RequestIsDestinationUsed(_message.Message):
    __slots__ = ["destination_id"]
    DESTINATION_ID_FIELD_NUMBER: _ClassVar[int]
    destination_id: int
    def __init__(self, destination_id: _Optional[int] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ["message", "status"]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    message: str
    status: str
    def __init__(self, status: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class ResponseIsDestinationUsed(_message.Message):
    __slots__ = ["is_used"]
    IS_USED_FIELD_NUMBER: _ClassVar[int]
    is_used: bool
    def __init__(self, is_used: bool = ...) -> None: ...

class SourceDeleteRequest(_message.Message):
    __slots__ = ["source_id"]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    source_id: int
    def __init__(self, source_id: _Optional[int] = ...) -> None: ...

class SourceRequest(_message.Message):
    __slots__ = ["group_id", "name", "source_id"]
    GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    group_id: int
    name: str
    source_id: int
    def __init__(self, source_id: _Optional[int] = ..., group_id: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...
