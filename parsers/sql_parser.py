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
                # Check if this is an escaped quote ('')
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
                # End of a statement
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
            else:
                current.append(char)

        i += 1

    # Catch anything left over (in case the file doesn't end with ;)
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
                    current.append("'")  # unescape '' into a single '
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

    # catch the last value (no trailing comma after it)
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
        # Grab everything after VALUES
        values_part = insert_stmt.split("VALUES", 1)[1]
        row_groups = extract_row_groups(values_part)

        for group in row_groups:
            values = split_values(group)
            record = build_record(columns, values)
            records.append(record)

    return columns, records