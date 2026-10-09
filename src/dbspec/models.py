"""DBSpec database schema model objects.

Defines the native Python objects used to represent SQL database schema
objects, including tables, columns and keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True)
class Identity:
    """A column identity definition.

    For columns with the `IDENTITY` property.
    """

    seed: int = 1
    increment: int = 1


@dataclass(frozen=True)
class Column:
    """A table column definition."""

    name: str
    datatype: str
    nullable: bool
    identity: Identity | None = None
    default: str | None = None


class ReferentialAction(StrEnum):
    """A foreign key referential action definition.

    For foreign keys with `ON DELETE`/`ON UPDATE` actions.
    """

    CASCADE = "CASCADE"
    NO_ACTION = "NO ACTION"
    SET_DEFAULT = "SET DEFAULT"
    SET_NULL = "SET NULL"


@dataclass(frozen=True)
class PrimaryKey:
    """A table primary key definition."""

    columns: list[str]


@dataclass(frozen=True)
class UniqueKey:
    """A table unique key definition."""

    columns: list[str]


@dataclass(frozen=True)
class ForeignKey:
    """A table foreign key definition."""

    columns: list[str]
    referenced_table: TableName
    referenced_columns: list[str]
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION
    on_update: ReferentialAction = ReferentialAction.NO_ACTION


@dataclass(frozen=True)
class TableName:
    """A table name definition.

    For fully-qualified table names, including their schema.
    """

    schema: str
    name: str


@dataclass(frozen=True)
class Table:
    """A database table definition."""

    identifier: TableName
    columns: dict[str, Column] = field(default_factory=dict)
    primary_key: PrimaryKey | None = None
    unique_keys: list[UniqueKey] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)


@dataclass(frozen=True)
class Database:
    """A SQL database definition."""

    tables: dict[TableName, Table] = field(default_factory=dict)
