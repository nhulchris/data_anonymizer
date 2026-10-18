-- Sample multi-table dump for demos: the same people appear in both
-- customers and orders, so cross-table consistency is visible.
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    id INT,
    name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    ssn VARCHAR(11)
);

CREATE TABLE orders (
    order_id INT,
    customer_name VARCHAR(100),
    customer_email VARCHAR(100),
    total VARCHAR(10)
);

INSERT INTO customers (id, name, email, phone, ssn) VALUES
(1, 'John Smith', 'john.smith@example.com', '612-555-1234', '123-45-6789'),
(2, 'Mary O''Brien', 'mary.obrien@example.org', '651-555-9876', '987-65-4321');

INSERT INTO orders (order_id, customer_name, customer_email, total) VALUES
(101, 'John Smith', 'john.smith@example.com', '19.99'),
(102, 'Mary O''Brien', 'mary.obrien@example.org', '5.00'),
(103, 'John Smith', 'john.smith@example.com', '42.10');

UPDATE customers SET phone = '000-000-0000' WHERE id = 99;
