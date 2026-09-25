from dataclasses import dataclass, field


@dataclass(frozen=True)
class Column:
    name: str
    datatype: str
    nullable: bool
    identity: bool = False
    default: str | None = None


@dataclass(frozen=True)
class PrimaryKey:
    columns: list[str]


@dataclass(frozen=True)
class ForeignKey:
    columns: list[str]
    referenced_table: str
    referenced_columns: list[str]


@dataclass(frozen=True)
class Table:
    schema: str
    name: str
    columns: dict[str, Column] = field(default_factory=dict)
    primary_key: PrimaryKey | None = None
    foreign_keys: list[ForeignKey] = field(default_factory=list)


@dataclass(frozen=True)
class Database:
    tables: dict[str, Table] = field(default_factory=dict)
