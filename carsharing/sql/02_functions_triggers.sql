-- 02_functions_triggers.sql : functions, stored procedure, triggers

-- Function: rental price = rounded-up hours (minimum 1 hour) * price_per_hour
CREATE OR REPLACE FUNCTION calc_rental_price(p_car_id INT, p_start TIMESTAMP, p_end TIMESTAMP)
RETURNS NUMERIC AS $$
DECLARE
    v_rate NUMERIC;
BEGIN
    SELECT price_per_hour INTO v_rate FROM cars WHERE car_id = p_car_id;
    IF v_rate IS NULL THEN
        RAISE EXCEPTION 'Car % not found', p_car_id;
    END IF;
    RETURN ROUND(GREATEST(1, CEIL(EXTRACT(EPOCH FROM (p_end - p_start)) / 3600.0)) * v_rate, 2);
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: total amount paid by one user
CREATE OR REPLACE FUNCTION user_total_spent(p_user_id INT)
RETURNS NUMERIC AS $$
    SELECT COALESCE(SUM(p.amount), 0)
    FROM rentals r JOIN payments p ON p.rental_id = r.rental_id
    WHERE r.user_id = p_user_id;
$$ LANGUAGE sql STABLE;

-- BEFORE trigger: validates new rentals and calculates the price of completed ones
CREATE OR REPLACE FUNCTION trg_rentals_before() RETURNS trigger AS $$
DECLARE
    v_car_status VARCHAR;
BEGIN
    IF TG_OP = 'INSERT' AND NEW.status IN ('booked', 'active') THEN
        SELECT status INTO v_car_status FROM cars WHERE car_id = NEW.car_id;
        IF v_car_status = 'maintenance' THEN
            RAISE EXCEPTION 'Car % is under maintenance and cannot be rented', NEW.car_id;
        END IF;
    END IF;

    IF NEW.status = 'completed' THEN
        IF NEW.end_time IS NULL THEN
            RAISE EXCEPTION 'Completed rental must have end_time';
        END IF;
        NEW.price := calc_rental_price(NEW.car_id, NEW.start_time, NEW.end_time);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS rentals_before ON rentals;
CREATE TRIGGER rentals_before
    BEFORE INSERT OR UPDATE ON rentals
    FOR EACH ROW EXECUTE FUNCTION trg_rentals_before();

-- AFTER trigger: keeps cars.status in sync with rentals.status
CREATE OR REPLACE FUNCTION trg_sync_car_status() RETURNS trigger AS $$
BEGIN
    IF NEW.status = 'active' THEN
        UPDATE cars SET status = 'rented' WHERE car_id = NEW.car_id;
    ELSIF NEW.status IN ('completed', 'cancelled') THEN
        UPDATE cars SET status = 'available'
        WHERE car_id = NEW.car_id
          AND status = 'rented'
          AND NOT EXISTS (SELECT 1 FROM rentals r
                          WHERE r.car_id = NEW.car_id AND r.status = 'active'
                            AND r.rental_id <> NEW.rental_id);
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sync_car_status ON rentals;
CREATE TRIGGER sync_car_status
    AFTER INSERT OR UPDATE OF status ON rentals
    FOR EACH ROW EXECUTE FUNCTION trg_sync_car_status();

-- Stored procedure: finish an active rental and register the payment (one atomic unit)
CREATE OR REPLACE PROCEDURE finish_rental(p_rental_id INT, p_method VARCHAR)
LANGUAGE plpgsql AS $$
DECLARE
    v_status VARCHAR;
    v_price  NUMERIC;
BEGIN
    SELECT status INTO v_status FROM rentals WHERE rental_id = p_rental_id FOR UPDATE;
    IF v_status IS NULL THEN
        RAISE EXCEPTION 'Rental % not found', p_rental_id;
    ELSIF v_status <> 'active' THEN
        RAISE EXCEPTION 'Rental % is not active (current status: %)', p_rental_id, v_status;
    END IF;

    UPDATE rentals
       SET end_time = localtimestamp, status = 'completed'      -- BEFORE trigger sets price
     WHERE rental_id = p_rental_id
    RETURNING price INTO v_price;

    INSERT INTO payments (rental_id, amount, method) VALUES (p_rental_id, v_price, p_method);
END;
$$;
