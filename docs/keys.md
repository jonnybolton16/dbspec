# Key Declarations

<a id="source"></a>In `DBSpec`, "keys" include primary keys, unique constraints[*](#note), and foreign keys.

### Primary Keys

Primary key declarations have the form:
```sql
PRIMARY KEY <column_list>
```
where
```sql
<column_list> = <column_name>, <column_name>, ...
```

For example:
```sql
PRIMARY KEY id
```

### Unique Constraints

Similarly, unique constraint declarations have the form:
```sql
UNIQUE <column_list>
```

For example:
```sql
UNIQUE (first_name, last_name)
```

### Foreign Keys

Foreign key declarations have the form:
```sql
FOREIGN KEY <column_list> REFERENCES <schema>.<table_name> <column_list> [ON DELETE <action>] [ON UPDATE <action>]
```
where
```sql
<action> = CASCADE | NO ACTION | SET DEFAULT | SET NULL
```

For example:
```sql
FOREIGN KEY(user_id) REFERENCES dbo.users(id) ON DELETE CASCADE
```

### Notes
- All keywords are **case-insensitive**.
- All `<column_name>`s in `<column_list>`, and both `<schema>` and `<table_name>` in a foreign key, must be [valid identifiers](identifiers.md). Additionally, if any of these match one of the keywords, it must be enclosed by square brackets.
- Parentheses around a `<column_list>` are optional. When omitted, the list must be separated from surrounding clauses by whitespace. When included, this separation is optional.
- Whitespace around the commas in a `<column_list>` is optional.
- If the `ON DELETE/UPDATE <action>` foreign key clause is not specified, the default `NO ACTION` is used.

#

<a id="note"></a>
\* While not typically known as "keys", unique constraints are used alongside primary and foreign keys to enforce database referential integrity, and are therefore classified as such [↩](#source)
