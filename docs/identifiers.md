# Identifiers

In `DBSpec`, the syntax for an **identifier** (such as a schema, table or column name) is based on `SQL Server` identifier syntax.

A valid identifier must either:
- consist solely of ASCII letters, digits and underscores
  - the first character must not be a digit
- be enclosed in square brackets (`[...]`), allowing other characters, whitespace or a leading digit to be included
  - a literal closing square bracket (`]`) inside the identifier must be escaped as `]]`

Regardless of whether square brackets are used, an identifier must not be empty.

## Examples

The following identifiers are valid:
- `dbo`
- `MY_TABLE`
- `Column0123456789`
- `_orgs`
- `[dbo]`
- `[123abc]`
- `[café]`
- `[aB '5~@]]#)]`

The following identifiers are invalid:
- `[]`  &rarr; *enclosed empty identifier*
- `123abc` &rarr; *leading digit without enclosed square brackets*
- `café` &rarr; *non-ASCII character without enclosed square brackets*
- `aB '5~@]]#)` &rarr; *non-alphanumeric/underscore characters without enclosed square brackets*
- `[aB '5~@]#)]` &rarr; *unescaped single closing square bracket inside the identifier*
- `123abc]` &rarr; *missing opening square bracket*
- `[123abc` &rarr; *missing closing square bracket*
- `[[123abc]]` &rarr; *the final `]]` is interpreted as an escaped `]`, leaving the identifier without a closing bracket*
