"""DBSpec database schema model objects.

Defines the data structures representing database schemas, including
tables, columns, primary keys and foreign keys.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Identity:
    """A database table column identity definition."""

    seed: int = 1
    increment: int = 1


@dataclass(frozen=True)
class Column:
    """A database table column definition."""

    name: str
    datatype: str
    nullable: bool
    identity: Identity | None = None
    default: str | None = None


@dataclass(frozen=True)
class PrimaryKey:
    """A database table primary key definition."""

    columns: list[str]


@dataclass(frozen=True)
class ForeignKey:
    """A database table foreign key definition."""

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
    foreign_keys: list[ForeignKey] = field(default_factory=list)


@dataclass(frozen=True)
class Database:
    """A database schema definition."""

    tables: dict[str, Table] = field(default_factory=dict)
