-- 04_views_roles.sql : views and authorization

CREATE OR REPLACE VIEW v_active_rentals AS
SELECT r.rental_id, u.user_name, u.phone_number,
       c.plate_number, c.brand, c.model, r.start_time
FROM rentals r
JOIN users u ON u.user_id = r.user_id
JOIN cars  c ON c.car_id  = r.car_id
WHERE r.status = 'active';

CREATE OR REPLACE VIEW v_user_revenue AS
SELECT u.user_id, u.user_name,
       COUNT(DISTINCT r.rental_id)  AS completed_rentals,
       COALESCE(SUM(p.amount), 0)   AS total_paid
FROM users u
LEFT JOIN rentals  r ON r.user_id = u.user_id AND r.status = 'completed'
LEFT JOIN payments p ON p.rental_id = r.rental_id
GROUP BY u.user_id, u.user_name;

-- Authorization: read-only analyst role and application role
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'carsharing_readonly') THEN
        CREATE ROLE carsharing_readonly NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'carsharing_app') THEN
        CREATE ROLE carsharing_app NOLOGIN;
    END IF;
END
$$;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO carsharing_readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON users, cars, rentals, payments TO carsharing_app;
GRANT SELECT ON v_active_rentals, v_user_revenue TO carsharing_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO carsharing_app;
REVOKE DELETE ON payments FROM carsharing_app;   -- payments are never deleted by the app
