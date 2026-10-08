# DBSpec

`DBSpec` simplifies SQL Server schema maintenance by utilising human-readable schema specifications.

The `.dbspec` file format is a friendly, easy-to-parse format for defining tables, columns and other SQL database objects. These files are automatically converted into **idempotent** SQL queries, allowing complex database schemas to be maintained via simple, readable specification files.

## Usage

A `DBSpec` file contains definitions of database objects, for example:

```sql # can I add the filename here?
TABLE dbo.users

id INT IDENTITY
name VARCHAR(100) NOT NULL
created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
archived_at DATETIME2 NULL
```

The `DBSpec` tooling can parse these definitions into native python objects, and can then generate and run the corresponding SQL queries required to bring the database into the specified state.

These queries are structured in an idepotent way, so a change to the schema can be applied without tyring to recreate what's already there.

## CLI

The `dbspec` CLI provides three core operations:
- `dbspec check` — parse and validate `DBSpec` files without connecting to a database.
- `dbspec diff` — compare the validated definitions with the current database schema, generating the SQL required to reconcile them.
- `dbspec execute` — apply the required changes to the database.

> **Note:** The `DBSpec` CLI is not yet developed. The interface shown above is illustrative.

## Grammar

The `DBSpec` tooling requies the `.dbspec` file format to follow strict grammar rules. See [DBSpec Grammar](docs/grammar.md) for the syntax and supported database object definitions.

## Status

`DBSpec` is currently under development.
