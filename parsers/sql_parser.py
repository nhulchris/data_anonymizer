"""SQL parser -- OWNER: SOPHIE.

Parses a SQL file (CREATE TABLE + INSERT statements) into a list of tables,
each with the same (headers, rows) shape used by csv_parser and json_parser,
plus a table name. Only INSERT statement values are extracted/replaced;
everything else (DROP, UPDATE, DELETE, comments) passes through unchanged.
"""

from __future__ import annotations


def extract_columns(create_statement: str) -> list[str]:
    """Pull column names out of a CREATE TABLE statement, in order."""

    start = create_statement.index("(")
    end = create_statement.rindex(")")
    body = create_statement[start + 1:end]

    skip_keywords = {
        "PRIMARY",
        "FOREIGN",
        "UNIQUE",
        "KEY",
        "CONSTRAINT",
        "CHECK",
    }

    columns = []

    for line in body.split(","):
        line = line.strip()

        if not line:
            continue

        column_name = line.split()[0]

        if column_name.upper() in skip_keywords:
            continue

        columns.append(column_name)

    return columns


def strip_comments(sql_text: str) -> str:
    """Remove SQL line comments (-- ...) while leaving quoted strings alone."""
    lines = sql_text.split("\n")
    cleaned_lines = []

    for line in lines:
        in_quote = False
        result = []
        i = 0
        while i < len(line):
            char = line[i]
            if in_quote:
                if char == "'":
                    if i + 1 < len(line) and line[i + 1] == "'":
                        result.append("''")
                        i += 2
                        continue
                    else:
                        in_quote = False
                result.append(char)
            else:
                if char == "'":
                    in_quote = True
                    result.append(char)
                elif char == "-" and i + 1 < len(line) and line[i + 1] == "-":
                    break  # rest of line is a comment
                else:
                    result.append(char)
            i += 1
        cleaned_lines.append("".join(result))

    return "\n".join(cleaned_lines)


def split_statements(sql_text: str) -> list[str]:
    """Split SQL text into statements, correctly ignoring semicolons
    and quote characters that appear inside quoted string values."""

    statements = []
    current = []
    in_quote = False
    i = 0

    while i < len(sql_text):
        char = sql_text[i]

        if in_quote:
            if char == "'":
                if i + 1 < len(sql_text) and sql_text[i + 1] == "'":
                    current.append("''")
                    i += 2
                    continue
                else:
                    in_quote = False
            current.append(char)

        else:
            if char == "'":
                in_quote = True
                current.append(char)
            elif char == ";":
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
            else:
                current.append(char)

        i += 1

    leftover = "".join(current).strip()
    if leftover:
        statements.append(leftover)

    return statements


def split_values(values_text: str) -> list[str]:
    """Split a VALUES list into individual values, respecting quotes."""

    values = []
    current = []
    in_quote = False
    i = 0

    while i < len(values_text):
        char = values_text[i]

        if in_quote:
            if char == "'":
                if i + 1 < len(values_text) and values_text[i + 1] == "'":
                    current.append("'")
                    i += 2
                    continue
                else:
                    in_quote = False
                    i += 1
                    continue
            current.append(char)
            i += 1

        else:
            if char == "'":
                in_quote = True
                i += 1
            elif char == ",":
                value = "".join(current).strip()
                values.append(value)
                current = []
                i += 1
            else:
                current.append(char)
                i += 1

    last_value = "".join(current).strip()
    values.append(last_value)

    return values


def extract_row_groups(text: str) -> list[str]:
    """Pull out the contents of each top-level (...) group in a VALUES list."""

    groups = []
    current = []
    depth = 0
    in_quote = False
    i = 0

    while i < len(text):
        char = text[i]

        if in_quote:
            if char == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    current.append("''")
                    i += 2
                    continue
                else:
                    in_quote = False
            current.append(char)
            i += 1
            continue

        if char == "'":
            in_quote = True
            if depth > 0:
                current.append(char)
            i += 1
            continue

        if char == "(":
            depth += 1
            if depth > 1:
                current.append(char)
            i += 1
            continue

        if char == ")":
            depth -= 1
            if depth == 0:
                groups.append("".join(current))
                current = []
            else:
                current.append(char)
            i += 1
            continue

        if depth > 0:
            current.append(char)
        i += 1

    return groups


def build_record(columns: list[str], values: list[str]) -> dict[str, str]:
    """Pair column names with their values for one row."""
    return dict(zip(columns, values))


def parse_table(create_statement: str, insert_statements: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    """Given one CREATE TABLE and its INSERT statement(s), return
    (columns, records) -- records is a list of dicts, one per row."""

    columns = extract_columns(create_statement)
    records = []

    for insert_stmt in insert_statements:
        values_part = insert_stmt.split("VALUES", 1)[1]
        row_groups = extract_row_groups(values_part)

        for group in row_groups:
            values = split_values(group)
            record = build_record(columns, values)
            records.append(record)

    return columns, records


def get_table_name(create_statement: str) -> str:
    """Pull the table name out of a CREATE TABLE statement."""
    start = create_statement.index("(")
    header = create_statement[:start]
    return header.split()[-1]


def get_insert_table_name(insert_statement: str) -> str:
    """Pull the table name out of an INSERT statement."""
    without_prefix = insert_statement[len("INSERT INTO"):].strip()
    return without_prefix.split()[0].rstrip("(")


def get_insert_columns(insert_statement: str, default_columns: list[str]) -> list[str]:
    """Get the column list for an INSERT, using the explicit list if given,
    otherwise falling back to the table's full column order."""
    upper = insert_statement.upper()
    values_idx = upper.index("VALUES")
    before_values = insert_statement[:values_idx]

    if "(" in before_values:
        start = before_values.index("(")
        end = before_values.rindex(")")
        col_text = before_values[start + 1:end]
        return [c.strip() for c in col_text.split(",") if c.strip()]

    return default_columns


def parse(sql_text: str) -> list[dict]:
    """Parse a SQL file into a list of tables:
    [{"name": str, "headers": list[str], "rows": list[list[str]]}, ...]
    Only INSERT statement values are extracted; everything else is ignored here
    and handled by serialize()."""

    sql_text = strip_comments(sql_text)
    statements = split_statements(sql_text)
    tables: dict[str, dict] = {}
    table_order: list[str] = []
    table_columns: dict[str, list[str]] = {}

    for statement in statements:
        stripped = statement.strip()
        upper = stripped.upper()

        if upper.startswith("CREATE TABLE"):
            name = get_table_name(stripped)
            columns = extract_columns(stripped)
            table_columns[name] = columns
            if name not in tables:
                tables[name] = {"name": name, "headers": columns, "rows": []}
                table_order.append(name)

        elif upper.startswith("INSERT INTO"):
            name = get_insert_table_name(stripped)
            if name not in table_columns:
                continue

            full_columns = table_columns[name]
            insert_columns = get_insert_columns(stripped, full_columns)

            values_idx = stripped.upper().index("VALUES")
            values_part = stripped[values_idx + len("VALUES"):]
            row_groups = extract_row_groups(values_part)

            for group in row_groups:
                values = split_values(group)
                record = build_record(insert_columns, values)
                row = [record.get(col, "") for col in full_columns]
                tables[name]["rows"].append(row)

    return [tables[name] for name in table_order]


def format_sql_value(value: str) -> str:
    """Format one value for writing back into SQL (quote text, leave numbers/booleans bare)."""
    stripped = value.strip()
    upper = stripped.upper()

    if upper in ("TRUE", "FALSE", "NULL"):
        return upper

    try:
        float(stripped)
        return stripped
    except ValueError:
        pass

    escaped = stripped.replace("'", "''")
    return f"'{escaped}'"


def build_insert_statement(table_name: str, headers: list[str], rows: list[list[str]]) -> str:
    """Build a fresh, valid INSERT statement from headers + rows."""
    row_lines = []
    for row in rows:
        formatted = [format_sql_value(v) for v in row]
        row_lines.append("(" + ", ".join(formatted) + ")")

    return (
        f"INSERT INTO {table_name} ({', '.join(headers)})\nVALUES\n"
        + ",\n".join(row_lines)
    )


def serialize(original_text: str, tables: list[dict]) -> str:
    """Rebuild the full SQL file: anonymized values go into INSERT statements,
    everything else (CREATE TABLE, DROP, UPDATE, DELETE, comments) stays untouched."""

    original_text = strip_comments(original_text)
    statements = split_statements(original_text)
    table_rows = {t["name"]: list(t["rows"]) for t in tables}
    table_headers = {t["name"]: t["headers"] for t in tables}
    table_columns: dict[str, list[str]] = {}
    output = []

    for statement in statements:
        stripped = statement.strip()
        upper = stripped.upper()

        if upper.startswith("CREATE TABLE"):
            name = get_table_name(stripped)
            table_columns[name] = extract_columns(stripped)
            output.append(stripped)

        elif upper.startswith("INSERT INTO"):
            name = get_insert_table_name(stripped)
            if name not in table_rows:
                output.append(stripped)
                continue

            values_idx = stripped.upper().index("VALUES")
            values_part = stripped[values_idx + len("VALUES"):]
            row_count = len(extract_row_groups(values_part))

            rows_for_this_insert = table_rows[name][:row_count]
            table_rows[name] = table_rows[name][row_count:]

            output.append(
                build_insert_statement(name, table_headers[name], rows_for_this_insert)
            )

        else:
            output.append(stripped)

    return ";\n\n".join(output) + ";\n"