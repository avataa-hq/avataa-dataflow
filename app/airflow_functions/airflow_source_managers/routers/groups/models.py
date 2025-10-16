from typing import Optional

from pydantic import BaseModel, Field
from enum import Enum


class SourceMappingTypes(str, Enum):
    OBJECT_DATA = "Object data"
    PM_DATA = "Pm data"
    GEO_DATA = "Geo data"
    OTHER_DATA = "Other data"


class SourceGroupModelInfo(BaseModel):
    id: int
    name: str
    source_type: SourceMappingTypes

    class Config:
        use_enum_values = True


class SourceGroupCreateModel(BaseModel):
    name: str = Field(min_length=1)
    source_type: SourceMappingTypes = Field(...)

    class Config:
        use_enum_values = True


class SourceGroupPatchModel(BaseModel):
    name: Optional[str]
    source_type: Optional[SourceMappingTypes]

    class Config:
        use_enum_values = True
