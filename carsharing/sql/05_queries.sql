-- 05_queries.sql : demonstration queries for the report / defence (run manually in psql)

-- 1. Selection, filtering, ordering
SELECT car_id, plate_number, brand, model, price_per_hour
FROM cars WHERE status = 'available' AND year >= 2021 ORDER BY price_per_hour DESC;

-- 2. Functions and operators (string, date, pattern matching)
SELECT UPPER(user_name) AS name, AGE(date_of_birth) AS age, email
FROM users WHERE email LIKE '%@gmail.com';

-- 3. Joins (LEFT): every user with the number of rentals (including 0)
SELECT u.user_name, COUNT(r.rental_id) AS rentals_count
FROM users u LEFT JOIN rentals r ON r.user_id = u.user_id
GROUP BY u.user_name ORDER BY rentals_count DESC;

-- 4. Aggregates + GROUP BY + HAVING: revenue per payment method
SELECT method, COUNT(*) AS payments, SUM(amount) AS total
FROM payments GROUP BY method HAVING SUM(amount) > 5000 ORDER BY total DESC;

-- 5. Nested subquery: users who spent more than the average user
SELECT user_name, total_paid FROM v_user_revenue
WHERE total_paid > (SELECT AVG(total_paid) FROM v_user_revenue);

-- 6. Set operations: users who never rented a car
SELECT user_id FROM users EXCEPT SELECT user_id FROM rentals;

-- 7. Window functions: ranking of users and running total per car
SELECT user_name, total_paid, RANK() OVER (ORDER BY total_paid DESC) AS rnk FROM v_user_revenue;

SELECT car_id, rental_id, price,
       SUM(price) OVER (PARTITION BY car_id ORDER BY start_time) AS running_total
FROM rentals WHERE status = 'completed';

-- 8. Recursive query: rentals started on each day of the first week of September
WITH RECURSIVE days(d) AS (
    SELECT DATE '2026-09-01'
    UNION ALL
    SELECT d + 1 FROM days WHERE d < DATE '2026-09-07'
)
SELECT d AS day, COUNT(r.rental_id) AS started
FROM days LEFT JOIN rentals r ON r.start_time::date = days.d
GROUP BY d ORDER BY d;

-- 9. Function and stored procedure
SELECT user_total_spent(1);
-- CALL finish_rental(10, 'card');

-- 10. Transaction with SAVEPOINT
BEGIN;
UPDATE cars SET status = 'maintenance' WHERE car_id = 5;
SAVEPOINT sp1;
UPDATE cars SET status = 'broken' WHERE car_id = 6;   -- violates CHECK -> error
ROLLBACK TO SAVEPOINT sp1;                            -- only the failed step is undone
COMMIT;

-- 11. Query optimization: compare plans with / without the index
EXPLAIN ANALYZE SELECT * FROM rentals WHERE user_id = 1;
-- DROP INDEX idx_rentals_user_id;  -> run EXPLAIN ANALYZE again and compare (Seq Scan vs Index Scan)

-- 12. Trigger / constraint checks (each must FAIL)
-- INSERT INTO rentals (user_id, car_id, start_time, status) VALUES (1, 8, now(), 'active');                -- car in maintenance
-- INSERT INTO rentals (user_id, car_id, start_time, status) VALUES (1, 3, '2026-10-21 10:00', 'active');   -- overlaps active rental
