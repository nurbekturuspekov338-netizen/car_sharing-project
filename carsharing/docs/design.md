# Design notes

## ERD -> relational schema
| Entity | Table | PK | FK |
|---|---|---|---|
| USERS | `users` | user_id | — |
| CAR | `cars` | car_id | — |
| RENTALS | `rentals` | rental_id | user_id -> users, car_id -> cars |
| PAYMENT | `payments` | payment_id | rental_id -> rentals |

Relationships (cardinality chosen for the model):
* USERS 1 — N RENTALS: a user can make many rentals, a rental belongs to one user.
* CAR 1 — N RENTALS: a car is rented many times (never twice at the same moment — `EXCLUDE` constraint).
* RENTALS 1 — N PAYMENTS: a rental is normally paid once, but several payments are allowed (e.g. fine/extra time).

## Changes with respect to the hand-drawn ERD
* `DATA` in RENTALS -> removed: it is the date part of `start_time` (derived attribute, would break 3NF-style redundancy).
* `AMOUNT` (floating label near PAYMENT) -> attribute `payments.amount`.
* `DATE` in PAYMENT -> `payments.payment_date` (DATE is a reserved word).
* `PRICE` in RENTALS -> `rentals.price`, calculated by trigger from `cars.price_per_hour` (added attribute) and rental duration.
* Added to CAR: `brand`, `model`, `price_per_hour`.
* STATUS values: cars `available/rented/maintenance`; rentals `booked/active/completed/cancelled`.

## Normalization
* 1NF: all attributes atomic, no repeating groups.
* 2NF: every table has a single-column surrogate PK, so there are no partial dependencies.
* 3NF/BCNF: non-key attributes depend only on the key (user data only in `users`, car data only in `cars`, payment data only in `payments`). `rentals.price` is the only derived value; it is stored on purpose as a historical snapshot (the car's hourly rate may change later).
