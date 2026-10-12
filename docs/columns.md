# Column Declarations

Column declarations have the form:
```sql
<column_name> <data_type> { IDENTITY[(<seed>, <increment>)] | [NOT] NULL [DEFAULT <expression>] }
```

For example:
```sql
id INT IDENTITY
id BIGINT IDENTITY(1000, 10)
name NVARCHAR(100) NOT NULL
is_archived BIT NULL
created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
```

Notes:
- The `IDENTITY`, `NOT`, `NULL` and `DEFAULT` keywords are
**case-insensitive**.
- If the `<column_name>` contains whitespace or matches one of the above keywords, it must be enclosed by square brackets. In such cases, the name itself cannot contain nested square brackets.
- For `IDENTITY` columns, neither or both the `<seed>` and `<increment>` must be provided. If they are provided, they must both be integers. If they are not provided, they both default to 1.
- All non-`IDENTITY` column declarations must specify their nullability explicitly. `IDENTITY` columns are implicitly `NOT
NULL`.
- When including the `DEFAULT` clause, the `<expression>` cannot be empty. The clause must follow the nullability specification, because `NULL` itself can appear in the `<expression>`. The validity of the `<expression>` is checked by SQL Server at execution time, not by `DBSpec` at parse time.
