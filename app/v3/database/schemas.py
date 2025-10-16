import json
from typing import Any

from sqlalchemy import (
    Column,
    Integer,
    String,
    UniqueConstraint,
    ForeignKey,
    Text,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import declarative_base, synonym, validates, relationship

from v3.routers.destinations.enums import ConType
from v3.routers.groups.models import SourceMappingTypes
from v3.routers.sources.models.general_model import SourceType
from v3.utils.encryption_utils import encrypt_data, decrypt_data

from v3.routers.sources.utils.exceptions import ValidationError

Base = declarative_base()


class SourceGroup(Base):
    __tablename__ = "source_groups"

    id: int = Column("id", Integer, primary_key=True)
    name: str = Column("name", String(32), nullable=False)
    source_type: str = Column("source_type", String(32), nullable=False)

    __table_args__ = (UniqueConstraint("name", name="source_groups_name_uc"),)

    @validates("source_type")
    def validate_source_type(self, key, value):
        if value not in [x.value for x in SourceMappingTypes]:
            raise ValidationError("Unknown source type!")
        return value


class Source(Base):
    __tablename__ = "sources"

    id: int = Column("id", Integer, primary_key=True)
    name: str = Column("name", String(32), nullable=False)
    con_type: str = Column("con_type", String(32), nullable=False)
    _con_data: Any = Column("con_data", Text, nullable=False, key="con_data")
    group_id: int = Column(
        "group_id",
        Integer,
        ForeignKey("source_groups.id", onupdate="cascade", ondelete="cascade"),
        nullable=False,
    )

    group = relationship("SourceGroup")

    __table_args__ = (
        UniqueConstraint("group_id", "name", name="sources_name_group_id_uc"),
    )

    @property
    def con_data(self):
        return self._con_data

    @con_data.setter
    def con_data(self, value):
        if isinstance(value, dict) is False:
            raise TypeError("Source.con_data value must be instance of dict")
        self._con_data = encrypt_data(json.dumps(value))

    con_data = synonym("_con_data", descriptor=con_data)

    def decoded_data(self):
        """Returns __dict__ with decrypted con_data"""
        def_dict = dict()
        def_dict.update(self.__dict__)
        def_dict["con_data"] = json.loads(decrypt_data(def_dict["_con_data"]))
        del def_dict["_con_data"]
        return def_dict

    @validates("con_type")
    def validate_con_type(self, key, value):
        if value not in [x.value for x in SourceType]:
            raise ValidationError("Unsupported connection type!")

        return value


class Destination(Base):
    __tablename__ = "destinations"

    id: int = Column("id", Integer)
    name: str = Column("name", String(32), nullable=False)
    con_type: str = Column("con_type", String(32), nullable=False)
    _con_data: Any = Column("con_data", Text, nullable=False, key="con_data")

    __table_args__ = (
        PrimaryKeyConstraint("id", name="destinations_pkey"),
        UniqueConstraint("name", name="destinations_name_uc"),
    )

    @property
    def con_data(self):
        return self._con_data

    @con_data.setter
    def con_data(self, value):
        if isinstance(value, dict) is False:
            raise TypeError("Source.con_data value must be instance of dict")
        self._con_data = encrypt_data(json.dumps(value))

    con_data = synonym("_con_data", descriptor=con_data)

    def decoded_data(self):
        """Returns __dict__ with decrypted con_data"""
        def_dict = dict()
        def_dict.update(self.__dict__)
        def_dict["con_data"] = json.loads(decrypt_data(def_dict["_con_data"]))
        del def_dict["_con_data"]
        return def_dict

    @validates("con_type")
    def validate_con_type(self, key, value):
        if value not in [x for x in ConType]:
            raise ValidationError("Unsupported connection type!")

        return value
