from pydantic import Field, BaseModel

from v3.routers.sources.models.general_model import (
    SourceConDataBaseModel,
    SourceModelBaseCreate,
    SourceType,
)


class InventoryModelBase(BaseModel):
    con_type: str | None = Field(
        default=SourceType.INVENTORY.value,
        regex=rf"^{SourceType.INVENTORY.value}$",
    )


class InventoryConnectionModel(SourceConDataBaseModel):
    tmo_id: int = Field(gt=0)


class InventoryModelCreate(SourceModelBaseCreate, InventoryModelBase):
    con_data: InventoryConnectionModel
