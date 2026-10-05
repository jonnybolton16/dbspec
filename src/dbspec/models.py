"""DBSpec database schema model objects.

Defines the native Python objects used to represent SQL database schema
objects, including tables, columns and keys.
"""

from dataclasses import dataclass, field


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
    referenced_table: str
    referenced_columns: list[str]


@dataclass(frozen=True)
class Table:
    """A database table definition."""

    schema: str
    name: str
    columns: dict[str, Column] = field(default_factory=dict)
    primary_key: PrimaryKey | None = None
    unique_keys: list[UniqueKey] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)


@dataclass(frozen=True)
class Database:
    """A SQL database definition."""

    tables: dict[str, Table] = field(default_factory=dict)
