# Table Declarations

Table declarations have the form:
```sql
TABLE <schema>.<table_name>
```

For example:
```sql
TABLE dbo.organisations
TABLE temp_schema.my_table
TABLE [schema@home].[escaped]]brackets]
```

Notes:
- The `TABLE` keyword is **case-insensitive**.
- Both `<schema>` and `<table_name>` must be [valid identifiers](identifiers.md)
