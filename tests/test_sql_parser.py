import pytest

from parsers.sql_parser import (
    extract_columns,
    split_statements,
    split_values,
    extract_row_groups,
    build_record,
    parse_table,
    strip_comments,
    parse,
    serialize,
)


# ---------------------------------------------------------
# extract_columns()
# ---------------------------------------------------------

def test_extract_columns_customers():
    create_statement = """
    CREATE TABLE customers (
        customer_id INT PRIMARY KEY,
        name VARCHAR(100),
        address VARCHAR(255),
        email VARCHAR(255),
        phone VARCHAR(20),
        loyalty_level VARCHAR(20),
        active BOOLEAN
    )
    """

    result = extract_columns(create_statement)

    assert result == [
        "customer_id",
        "name",
        "address",
        "email",
        "phone",
        "loyalty_level",
        "active",
    ]


# ---------------------------------------------------------
# split_statements()
# ---------------------------------------------------------

def test_split_statements():
    sql_text = """
    DROP TABLE IF EXISTS customers;

    CREATE TABLE customers (
        customer_id INT,
        name VARCHAR(100)
    );

    INSERT INTO customers VALUES
    (101, 'John Smith'),
    (102, 'Robert O''Connor');

    UPDATE customers
    SET name = 'Jane Smith'
    WHERE customer_id = 101;
    """

    result = split_statements(sql_text)

    assert len(result) == 4
    assert result[0].startswith("DROP TABLE IF EXISTS customers")
    assert result[1].startswith("CREATE TABLE customers")
    assert result[2].startswith("INSERT INTO customers VALUES")
    assert result[3].startswith("UPDATE customers")


def test_split_statements_does_not_split_escaped_apostrophe():
    sql_text = """
    INSERT INTO customers VALUES
    (101, 'Robert O''Connor');
    """

    result = split_statements(sql_text)

    assert len(result) == 1
    assert "Robert O''Connor" in result[0]


def test_split_statements_ignores_semicolon_inside_quotes():
    sql_text = "INSERT INTO notes VALUES (1, 'Call me; it is urgent');"

    result = split_statements(sql_text)

    assert len(result) == 1
    assert "Call me; it is urgent" in result[0]


# ---------------------------------------------------------
# split_values()
# ---------------------------------------------------------

def test_split_values_unescapes_apostrophe():
    values = "101, 'Robert O''Connor', 'robert@example.com'"
    result = split_values(values)
    assert result == ["101", "Robert O'Connor", "robert@example.com"]


def test_split_values_keeps_comma_inside_address():
    values = (
        "101, 'John Smith', "
        "'123 Main Street, Suite 200', "
        "'john@example.com'"
    )
    result = split_values(values)
    assert result == [
        "101",
        "John Smith",
        "123 Main Street, Suite 200",
        "john@example.com",
    ]


def test_split_values_handles_normal_values():
    values = (
        "101, 'John Smith', '123 Main Street', "
        "'john@example.com', '612-555-1234', 'Gold', TRUE"
    )
    result = split_values(values)
    assert result == [
        "101",
        "John Smith",
        "123 Main Street",
        "john@example.com",
        "612-555-1234",
        "Gold",
        "TRUE",
    ]


# ---------------------------------------------------------
# extract_row_groups()
# ---------------------------------------------------------

def test_extract_row_groups_multiple_rows():
    values_text = """
    (101, 'John Smith', '123 Main Street', 'john@example.com'),
    (102, 'Jane Smith', '456 Oak Avenue', 'jane@example.com'),
    (103, 'Robert O''Connor', '789 Pine Street', 'robert@example.com')
    """

    result = extract_row_groups(values_text)

    assert len(result) == 3
    assert result[0] == (
        "101, 'John Smith', '123 Main Street', 'john@example.com'"
    )
    assert result[2] == (
        "103, 'Robert O''Connor', '789 Pine Street', 'robert@example.com'"
    )


def test_extract_row_groups_keeps_comma_inside_address():
    values_text = """
    (101, 'John Smith', '123 Main Street, Suite 200', 'john@example.com'),
    (102, 'Jane Smith', '456 Oak Avenue', 'jane@example.com')
    """

    result = extract_row_groups(values_text)

    assert len(result) == 2
    assert result[0] == (
        "101, 'John Smith', "
        "'123 Main Street, Suite 200', "
        "'john@example.com'"
    )


# ---------------------------------------------------------
# build_record()
# ---------------------------------------------------------

def test_build_record():
    columns = ["customer_id", "name", "email"]
    values = ["101", "John Smith", "john@example.com"]
    result = build_record(columns, values)
    assert result == {
        "customer_id": "101",
        "name": "John Smith",
        "email": "john@example.com",
    }


# ---------------------------------------------------------
# parse_table()
# ---------------------------------------------------------

def test_parse_table_two_insert_statements():
    create_statement = """
    CREATE TABLE customers (
        customer_id INT PRIMARY KEY,
        name VARCHAR(100),
        address VARCHAR(255),
        email VARCHAR(255),
        phone VARCHAR(20),
        loyalty_level VARCHAR(20),
        active BOOLEAN
    )
    """

    insert_statements = [
        """
        INSERT INTO customers VALUES
        (101, 'John Smith', '123 Main Street',
         'john@example.com', '612-555-1001', 'Gold', TRUE),
        (102, 'Jane Smith', '456 Oak Avenue',
         'jane@example.com', '612-555-1002', 'Silver', TRUE)
        """,
        """
        INSERT INTO customers VALUES
        (103, 'Robert O''Connor', '789 Pine Street',
         'robert@example.com', '612-555-1003', 'Bronze', FALSE),
        (104, 'Mary Johnson', '111 Cedar Street',
         'mary@example.com', '612-555-1004', 'Gold', TRUE)
        """
    ]

    columns, records = parse_table(create_statement, insert_statements)

    assert columns == [
        "customer_id", "name", "address", "email",
        "phone", "loyalty_level", "active",
    ]
    assert len(records) == 4
    assert records[0]["customer_id"] == "101"
    assert records[0]["name"] == "John Smith"
    assert records[2]["name"] == "Robert O'Connor"
    assert records[3]["name"] == "Mary Johnson"


# ---------------------------------------------------------
# strip_comments()
# ---------------------------------------------------------

def test_strip_comments_removes_full_line_comment():
    sql_text = "-- this is a comment\nCREATE TABLE x (id INT);"
    result = strip_comments(sql_text)
    assert "this is a comment" not in result
    assert "CREATE TABLE x (id INT);" in result


def test_strip_comments_removes_trailing_comment():
    sql_text = "DROP TABLE customers; -- drop it\nCREATE TABLE x (id INT);"
    result = strip_comments(sql_text)
    assert "drop it" not in result
    assert "DROP TABLE customers;" in result


def test_strip_comments_preserves_double_dash_inside_quotes():
    sql_text = "INSERT INTO notes VALUES (1, 'double--dash in text');"
    result = strip_comments(sql_text)
    assert "double--dash in text" in result


def test_strip_comments_preserves_escaped_apostrophe():
    sql_text = "INSERT INTO customers VALUES (1, 'Robert O''Connor'); -- a note"
    result = strip_comments(sql_text)
    assert "Robert O''Connor" in result
    assert "a note" not in result


# ---------------------------------------------------------
# parse() -- full multi-table file
# ---------------------------------------------------------

SAMPLE_SQL = """
-- Sample file for testing
-- Multiple tables, multiple INSERTs, comments, apostrophes

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    name VARCHAR(100),
    address VARCHAR(200),
    email VARCHAR(100)
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_name VARCHAR(100),
    amount DECIMAL(10,2)
);

-- CUSTOMERS
INSERT INTO customers
(customer_id, name, address, email)
VALUES
(101, 'Daniel Carter', '1824 Cedar Lane, Minneapolis, MN', 'daniel.carter@example.com'),
(102, 'Robert O''Connor', '1777 Grand Avenue, St. Paul, MN', 'robert.oconnor@example.com');

-- a second INSERT for the same table
INSERT INTO customers VALUES
(103, 'Priya Nair', '744 Summit Avenue, St. Paul, MN', 'priya.nair@example.com');

-- ORDERS
INSERT INTO orders VALUES
(5001, 'Daniel Carter', 49.99),
(5002, 'Robert O''Connor', 89.00);

-- this should remain untouched
UPDATE customers SET active = TRUE WHERE customer_id = 101;

-- this should also remain untouched
DELETE FROM orders WHERE order_id = 9999;
"""


def test_parse_returns_all_tables_with_correct_row_counts():
    tables = parse(SAMPLE_SQL)
    names = [t["name"] for t in tables]

    assert "customers" in names
    assert "orders" in names

    customers = next(t for t in tables if t["name"] == "customers")
    orders = next(t for t in tables if t["name"] == "orders")

    assert len(customers["rows"]) == 3  # two INSERTs: 2 + 1
    assert len(orders["rows"]) == 2


def test_parse_handles_apostrophe_in_name():
    tables = parse(SAMPLE_SQL)
    customers = next(t for t in tables if t["name"] == "customers")
    name_idx = customers["headers"].index("name")
    names = [row[name_idx] for row in customers["rows"]]

    assert "Robert O'Connor" in names  # unescaped, single apostrophe


def test_parse_ignores_comments():
    tables = parse(SAMPLE_SQL)
    customers = next(t for t in tables if t["name"] == "customers")
    name_idx = customers["headers"].index("name")
    names = [row[name_idx] for row in customers["rows"]]

    assert "Daniel Carter" in names
    assert "Priya Nair" in names


# ---------------------------------------------------------
# serialize() -- round trip + anonymization
# ---------------------------------------------------------

def test_serialize_preserves_non_insert_statements():
    tables = parse(SAMPLE_SQL)
    output = serialize(SAMPLE_SQL, tables)

    assert "DROP TABLE IF EXISTS orders" in output
    assert "CREATE TABLE customers" in output
    assert "UPDATE customers SET active = TRUE" in output
    assert "DELETE FROM orders WHERE order_id = 9999" in output


def test_serialize_round_trip_preserves_values_when_unmodified():
    tables = parse(SAMPLE_SQL)
    output = serialize(SAMPLE_SQL, tables)

    assert "Daniel Carter" in output
    assert "Robert O'Connor" in output or "Robert O''Connor" in output
    assert "Priya Nair" in output


def test_serialize_reflects_modified_values():
    tables = parse(SAMPLE_SQL)
    customers = next(t for t in tables if t["name"] == "customers")
    name_idx = customers["headers"].index("name")

    for row in customers["rows"]:
        if row[name_idx] == "Daniel Carter":
            row[name_idx] = "Test Anonymized Name"

    output = serialize(SAMPLE_SQL, tables)

    assert "Test Anonymized Name" in output

    # Only check within the customers section specifically --
    # "Daniel Carter" legitimately still appears in the orders table,
    # which we never modified.
    orders_idx = output.find("INSERT INTO orders")
    customers_section = output[:orders_idx]
    assert "Daniel Carter" not in customers_section


def test_serialize_does_not_modify_other_tables_unexpectedly():
    tables = parse(SAMPLE_SQL)
    customers = next(t for t in tables if t["name"] == "customers")
    name_idx = customers["headers"].index("name")

    for row in customers["rows"]:
        if row[name_idx] == "Daniel Carter":
            row[name_idx] = "Test Anonymized Name"

    output = serialize(SAMPLE_SQL, tables)

    # orders table still has the original name since we didn't touch it
    orders_idx = output.find("INSERT INTO orders")
    orders_section = output[orders_idx:]
    assert "Daniel Carter" in orders_section