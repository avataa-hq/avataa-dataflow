from pydantic import BaseModel, Field


class Storage(BaseModel):
    name: str = Field(min_length=1)
    conn_type: str | None = Field(alias="connType", min_length=1)
    host: str | None = Field(min_length=1)
    port: str | int | None = Field(min_length=1, gt=0)
    user: str | None = Field(min_length=1)
    password: str | None = Field(min_length=1)


class SourceGroup(BaseModel):
    name: str = Field(min_length=1)
    storage: Storage | None


class SourceField(BaseModel):
    """Actual source model"""

    name: str = Field(min_length=1)
    status: bool
    source: str = Field(min_length=1)


class DataSource(BaseModel):
    """Model that groups sources"""

    name: str
    status: bool
    fields: list[SourceField] = Field(alias="child")
