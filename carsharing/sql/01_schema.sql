-- 01_schema.sql : DDL for the Car Sharing database (PostgreSQL 15+)
-- ER diagram -> relations:  USERS 1--N RENTALS N--1 CARS,  RENTALS 1--N PAYMENTS
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- needed for the EXCLUDE constraint below

DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS rentals  CASCADE;
DROP TABLE IF EXISTS cars     CASCADE;
DROP TABLE IF EXISTS users    CASCADE;

CREATE TABLE users (
    user_id       SERIAL       PRIMARY KEY,
    user_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL UNIQUE,
    date_of_birth DATE         NOT NULL CHECK (date_of_birth <= CURRENT_DATE - INTERVAL '18 years'),
    phone_number  VARCHAR(20)  NOT NULL UNIQUE
);

CREATE TABLE cars (
    car_id         SERIAL        PRIMARY KEY,
    plate_number   VARCHAR(15)   NOT NULL UNIQUE,
    brand          VARCHAR(50)   NOT NULL,          -- added: not in the ERD, makes the data realistic
    model          VARCHAR(50)   NOT NULL,          -- added
    year           INTEGER       NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    price_per_hour NUMERIC(10,2) NOT NULL CHECK (price_per_hour > 0),   -- added: used to compute rentals.price
    status         VARCHAR(20)   NOT NULL DEFAULT 'available'
                   CHECK (status IN ('available', 'rented', 'maintenance'))
);

CREATE TABLE rentals (
    rental_id  SERIAL        PRIMARY KEY,
    user_id    INTEGER       NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    car_id     INTEGER       NOT NULL REFERENCES cars(car_id)   ON DELETE RESTRICT,
    start_time TIMESTAMP     NOT NULL,
    end_time   TIMESTAMP,                                   -- NULL while the rental is still running
    price      NUMERIC(10,2) CHECK (price >= 0),            -- filled by trigger when rental is completed
    status     VARCHAR(20)   NOT NULL DEFAULT 'active'
               CHECK (status IN ('booked', 'active', 'completed', 'cancelled')),
    CONSTRAINT rentals_time_order CHECK (end_time IS NULL OR end_time > start_time),
    -- one car cannot be booked/active in two overlapping periods
    CONSTRAINT rentals_no_overlap EXCLUDE USING gist (
        car_id WITH =,
        tsrange(start_time, end_time) WITH &&
    ) WHERE (status IN ('booked', 'active'))
);

CREATE TABLE payments (
    payment_id   SERIAL        PRIMARY KEY,
    rental_id    INTEGER       NOT NULL REFERENCES rentals(rental_id) ON DELETE CASCADE,
    payment_date TIMESTAMP     NOT NULL DEFAULT localtimestamp,
    amount       NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    method       VARCHAR(20)   NOT NULL CHECK (method IN ('card', 'cash', 'kaspi', 'transfer'))
);

-- Indexes on foreign keys and frequently filtered columns
CREATE INDEX idx_rentals_user_id   ON rentals(user_id);
CREATE INDEX idx_rentals_car_id    ON rentals(car_id);
CREATE INDEX idx_rentals_status    ON rentals(status);
CREATE INDEX idx_payments_rental   ON payments(rental_id);
