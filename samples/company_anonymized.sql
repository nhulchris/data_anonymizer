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

INSERT INTO customers (id, name, email, phone, ssn)
VALUES
(1, 'Ann King', 'fitzpatrickdamon@example.com', '076-333-0767', '080-72-1188'),
(2, 'Jose Bell', 'matthew00@example.org', '006-312-9594', '346-78-3412');

INSERT INTO orders (order_id, customer_name, customer_email, total)
VALUES
(101, 'Ann King', 'fitzpatrickdamon@example.com', 19.99),
(102, 'Jose Bell', 'matthew00@example.org', 5.00),
(103, 'Ann King', 'fitzpatrickdamon@example.com', 42.10);

UPDATE customers SET phone = '000-000-0000' WHERE id = 99;
