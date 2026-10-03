
from parsers.sql_parser import (
    extract_columns,
    split_statements,
    split_values,
    extract_row_groups,
    build_record,
    parse_table,
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


# ---------------------------------------------------------
# split_values()
# ---------------------------------------------------------

def test_split_values_unescapes_apostrophe():
    values = "101, 'Robert O''Connor', 'robert@example.com'"

    result = split_values(values)

    assert result == [
        "101",
        "Robert O'Connor",
        "robert@example.com",
    ]


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

    assert result[1] == (
        "102, 'Jane Smith', '456 Oak Avenue', 'jane@example.com'"
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
    columns = [
        "customer_id",
        "name",
        "email",
    ]

    values = [
        "101",
        "John Smith",
        "john@example.com",
    ]

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

    columns, records = parse_table(
        create_statement,
        insert_statements
    )

    assert columns == [
        "customer_id",
        "name",
        "address",
        "email",
        "phone",
        "loyalty_level",
        "active",
    ]

    assert len(records) == 4

    assert records[0]["customer_id"] == "101"
    assert records[0]["name"] == "John Smith"

    assert records[1]["customer_id"] == "102"
    assert records[1]["name"] == "Jane Smith"

    assert records[2]["customer_id"] == "103"
    assert records[2]["name"] == "Robert O'Connor"

    assert records[3]["customer_id"] == "104"
    assert records[3]["name"] == "Mary Johnson"
