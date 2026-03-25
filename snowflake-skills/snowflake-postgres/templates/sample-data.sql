-- =============================================================
-- Snowflake Postgres — Sample Ecommerce Data
-- =============================================================
-- Run this via psql against your Postgres instance (not Snowflake).
-- Creates customers, products, and orders tables with sample data.
-- =============================================================

-- Create customers table
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    city VARCHAR(50)
);

-- Create products table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2)
);

-- Create orders table with foreign keys
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    order_date DATE DEFAULT CURRENT_DATE,
    customer_id INT,
    product_id INT,
    quantity INT,
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_order_product FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Insert sample customers
INSERT INTO customers (first_name, last_name, email, city) VALUES
    ('Alice', 'Smith', 'alice@example.com', 'New York'),
    ('Bob', 'Johnson', 'bob@example.com', 'Los Angeles'),
    ('Charlie', 'Brown', 'charlie@example.com', 'Chicago'),
    ('Diana', 'Prince', 'diana@example.com', 'Houston'),
    ('Evan', 'Wright', 'evan@example.com', 'Phoenix'),
    ('Fiona', 'Gallagher', 'fiona@example.com', 'Chicago'),
    ('George', 'Martin', 'george@example.com', 'Santa Fe'),
    ('Hannah', 'Lee', 'hannah@example.com', 'Los Angeles'),
    ('Ian', 'Malcolm', 'ian@example.com', 'Austin'),
    ('Julia', 'Roberts', 'julia@example.com', 'New York');

-- Insert sample products
INSERT INTO products (product_name, category, price) VALUES
    ('Wireless Mouse', 'Electronics', 25.99),
    ('Mechanical Keyboard', 'Electronics', 120.50),
    ('Gaming Monitor', 'Electronics', 300.00),
    ('Yoga Mat', 'Fitness', 20.00),
    ('Dumbbell Set', 'Fitness', 55.00),
    ('Running Shoes', 'Footwear', 89.99),
    ('Leather Jacket', 'Apparel', 150.00),
    ('Coffee Maker', 'Kitchen', 45.00),
    ('Blender', 'Kitchen', 30.00),
    ('Novel: The Great Gatsby', 'Books', 12.50);

-- Insert sample orders
INSERT INTO orders (order_date, customer_id, product_id, quantity) VALUES
    ('2024-10-01', 1, 1, 1),
    ('2024-10-02', 2, 3, 1),
    ('2024-10-03', 1, 10, 2),
    ('2024-10-04', 3, 2, 1),
    ('2024-10-05', 4, 6, 1),
    ('2024-10-06', 5, 8, 1),
    ('2024-10-07', 2, 2, 1),
    ('2024-10-08', 6, 4, 3),
    ('2024-10-09', 7, 10, 1),
    ('2024-10-10', 8, 7, 1);

-- =============================================================
-- Example queries
-- =============================================================

-- Order details with customer and product info
SELECT
    o.order_id,
    o.order_date,
    c.first_name || ' ' || c.last_name AS customer_name,
    p.product_name,
    p.price,
    o.quantity,
    (p.price * o.quantity) AS total_cost
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON o.product_id = p.product_id;

-- Top 3 customers by spend
SELECT
    c.first_name,
    c.last_name,
    COUNT(o.order_id) AS number_of_orders,
    SUM(p.price * o.quantity) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN products p ON o.product_id = p.product_id
GROUP BY c.first_name, c.last_name
ORDER BY total_spent DESC
LIMIT 3;

-- Sales by product category
SELECT
    p.category,
    SUM(o.quantity) AS items_sold,
    SUM(p.price * o.quantity) AS revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;
