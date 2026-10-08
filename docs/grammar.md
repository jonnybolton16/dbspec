# DBSpec Grammar

A `DBSpec` file contains human-readable schema and definitions which are to be turned into idempotent SQL queries for execution in the database.

A single file can define one of the following:
- [a table](#tables)
- [an RLS predicate](#rls-predicates)
- [a trigger](#triggers)
- [a stored procedure](#stored-procedures)

## Tables

A `DBSpec` file defining a table has the form:
```sql
<table_declaration>

<column_declaration>
<column_declaration>
...

@@ KEYS
<key_declaration>
<key_declaration>
...

@@ CHECKS
<check_declaration>
<check_declaration>
...

@@ RLS POLICIES
<rls_declaration>
<rls_declaration>
...

@@ TRIGGERS
<trigger_declaration>
<trigger_declaration>
...

@@ INDEXES
<index_declaration>
<index_declaration>
...
```

The first line of the file must be a [table declaration](tables.md), followed by a blank line.

The next section contains all of the table's [column declarations](columns.md). These may form a single block, or they may be grouped into separated blocks separated by blank lines. There may also may be single-line comments (starting with `--`) interleaved between them.

Following the column declarations, any [keys](keys.md), [checks](checks.md), [RLS policies](rls.md), [triggers](triggers.md) and [indexes](indexes.md) can be declared. The header `@@ <CATEGORY>` must be included to delimit these declarations from the columns, and from each other.

The grammar for each type of declaration is described on its respective page.

## RLS Predicates

A `DBSpec` file defining an RLS predicate has the form:
```
TODO
```

## Triggers

A `DBSpec` file defining a trigger has the form:
```
TODO
```

## Stored Procedures

A `DBSpec` file defining a stored procedure has the form:
```
TODO
```
