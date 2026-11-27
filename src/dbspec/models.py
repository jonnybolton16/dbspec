"""DBSpec database schema model objects.

Defines Python objects for representing SQL database schema elements,
including tables, columns, and keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from dbspec.errors import DBSpecModelError


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

    def __str__(self) -> str:
        """Return the column name."""
        return self.name


class ReferentialAction(StrEnum):
    """A foreign key referential action definition.

    For foreign keys with `ON DELETE`/`ON UPDATE` actions.
    """

    CASCADE = "CASCADE"
    NO_ACTION = "NO ACTION"
    SET_DEFAULT = "SET DEFAULT"
    SET_NULL = "SET NULL"


@dataclass(frozen=True)
class Key:
    """A base table key definition.

    Subclasses include `PrimaryKey`, `UniqueKey` and `ForeignKey`.
    """

    columns: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate that the key has at least one column.

        Existence of column(s) is checked at table level.
        """
        object.__setattr__(self, "columns", tuple(self.columns))

        if not self.columns:
            msg = f"{type(self).__name__} must have at least one column"
            raise DBSpecModelError(msg)


@dataclass(frozen=True)
class PrimaryKey(Key):
    """A table primary key definition."""


@dataclass(frozen=True)
class UniqueKey(Key):
    """A table unique key definition."""


@dataclass(frozen=True)
class ForeignKey(Key):
    """A table foreign key definition."""

    referenced_table: TableName
    referenced_columns: tuple[str, ...]
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION
    on_update: ReferentialAction = ReferentialAction.NO_ACTION

    def __post_init__(self) -> None:
        """Validate the column counts on both sides of the reference.

        Existence and validity of reference targets and referential
        actions are checked at table/database level.
        """
        super().__post_init__()

        object.__setattr__(
            self, "referenced_columns", tuple(self.referenced_columns)
        )

        if len(self.columns) != len(self.referenced_columns):
            msg = (
                f"{type(self).__name__} must have the same "
                "number of local and referenced columns"
            )
            raise DBSpecModelError(msg)


@dataclass(frozen=True)
class TableName:
    """A table name definition.

    For fully-qualified table names, including their schema.
    """

    schema: str
    name: str

    def __str__(self) -> str:
        """Return the fully-qualified table name."""
        return f"{self.schema}.{self.name}"


@dataclass(frozen=True)
class Table:
    """A database table definition."""

    identifier: TableName
    columns: dict[str, Column] = field(default_factory=dict)
    primary_key: PrimaryKey | None = None
    unique_keys: list[UniqueKey] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)

    def __str__(self) -> str:
        """Return the fully-qualified table name.

        Delegate to the identifier's __str__ method.
        """
        return str(self.identifier)

    def add_column(self, column: Column) -> None:
        """Add a column to the table.

        Raises:
          DBSpecModelError: If
           - the table already has a column with the same name
           - the column is a second identity column
        """
        if column.name in self.columns:
            msg = f"Table already has a column named {str(column)!r}"
            raise DBSpecModelError(msg)

        if column.identity and any(
            col.identity for col in self.columns.values()
        ):
            msg = "Table already has an identity column"
            raise DBSpecModelError(msg)

        self.columns[column.name] = column

    def add_key(self, key: Key) -> None:
        """Add a key to the table.

        Raises:
          DBSpecModelError: If:
           - the table has no columns
           - the key's columns do not exist in the table
           - the key is a second primary key
           - the key is a primary key whose column(s) are nullable
           - the key is a foreign key whose column(s) are incompatible
             with its referential actions

          Existence and validity of foreign-key reference targets are
          checked at database level.
        """
        if not self.columns:
            msg = (
                "Cannot add a key to a table with no columns; "
                "add columns first"
            )
            raise DBSpecModelError(msg)

        if missing := [col for col in key.columns if col not in self.columns]:
            msg = (
                f"Key colum(s) {', '.join(map(repr, missing))} "
                "do not exist in the table"
            )
            raise DBSpecModelError(msg)

        if isinstance(key, PrimaryKey):
            if self.primary_key is not None:
                msg = "Table already has a primary key"
                raise DBSpecModelError(msg)

            if any(self.columns[col].nullable for col in key.columns):
                msg = f"{type(key).__name__} cannot have nullable columns"
                raise DBSpecModelError(msg)

            object.__setattr__(self, "primary_key", key)

        elif isinstance(key, UniqueKey):
            self.unique_keys.append(key)

        elif isinstance(key, ForeignKey):
            if ReferentialAction.SET_DEFAULT in (
                key.on_delete,
                key.on_update,
            ) and not all(
                self.columns[col].default is not None
                or self.columns[col].nullable
                for col in key.columns
            ):
                msg = (
                    f"{type(key).__name__} can only use SET DEFAULT when "
                    "each of its columns has a default or is nullable"
                )
                raise DBSpecModelError(msg)

            if ReferentialAction.SET_NULL in (
                key.on_delete,
                key.on_update,
            ) and not all(self.columns[col].nullable for col in key.columns):
                msg = (
                    f"{type(key).__name__} can only use SET NULL "
                    "when each of its columns is nullable"
                )
                raise DBSpecModelError(msg)

            self.foreign_keys.append(key)


@dataclass(frozen=True)
class Database:
    """A SQL database definition."""

    tables: dict[TableName, Table] = field(default_factory=dict)

    def add_table(self, table: Table) -> None:
        """Add a table to the database.

        Raises:
          DBSpecModelError: If the database already has a table with the
           same identifier.
        """
        if table.identifier in self.tables:
            msg = f"Database already has a table named {str(table)!r}"
            raise DBSpecModelError(msg)

        self.tables[table.identifier] = table
