# Car Sharing — Databases project (KBTU, CSE1301)

PostgreSQL database + Flask REST API (psycopg3, connection pool, SERIALIZABLE transactions).

## 1. Requirements
Python 3.10+, PostgreSQL 15+.

## 2. Setup
```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

createdb -U postgres carsharing     # or: CREATE DATABASE carsharing; in psql
cp .env.example .env                # edit user/password in DATABASE_URL

python init_db.py                   # schema + triggers + seed data + views + roles
python run.py                       # http://127.0.0.1:5000
```

## 3. Project structure
| Path | Purpose |
|---|---|
| `sql/01_schema.sql` | DDL: tables, PK/FK, UNIQUE, CHECK, EXCLUDE, indexes |
| `sql/02_functions_triggers.sql` | functions, stored procedure `finish_rental`, triggers |
| `sql/04_views_roles.sql` | views, roles and GRANT/REVOKE |
| `sql/05_queries.sql` | demo queries: joins, aggregates, subqueries, window functions, recursive CTE, SAVEPOINT, EXPLAIN |
| `init_db.py` | creates schema and seeds data (`executemany`) |
| `app/db.py` | ConnectionPool (min=2, max=8), `transaction()`, `serializable()`, `with_retry()` |
| `app/errors.py` | psycopg3 exceptions -> HTTP codes |
| `app/routes.py` | endpoints |
| `docs/design.md` | ERD -> relational mapping, normalization |

## 4. Endpoints and sample curl
```bash
curl http://127.0.0.1:5000/users
curl "http://127.0.0.1:5000/users?name=ar"
curl -X POST http://127.0.0.1:5000/users -H "Content-Type: application/json" \
     -d '{"user_name":"Test User","email":"test@gmail.com","date_of_birth":"2000-01-01","phone_number":"+77019999999"}'
curl -X PUT  http://127.0.0.1:5000/users/1 -H "Content-Type: application/json" \
     -d '{"user_name":"Arman B.","email":"arman.bekov@gmail.com","phone_number":"+77011110001"}'
curl -X DELETE http://127.0.0.1:5000/users/10

curl "http://127.0.0.1:5000/cars?status=available"
curl "http://127.0.0.1:5000/rentals?user_id=1"
curl -X POST http://127.0.0.1:5000/rentals -H "Content-Type: application/json" -d '{"user_id":1,"car_id":2}'
curl -X POST http://127.0.0.1:5000/rentals/10/finish -H "Content-Type: application/json" -d '{"method":"kaspi"}'
curl "http://127.0.0.1:5000/payments?rental_id=1"
curl http://127.0.0.1:5000/reports/top-users
curl http://127.0.0.1:5000/health
```

## 5. Error handling checks
| Test | Expected |
|---|---|
| POST /users with an existing email | 409 |
| POST /users without `email` | 400 |
| POST /rentals for car 8 (maintenance) | 422 |
| POST /rentals for car 3 (already rented) | 409 |
| POST /rentals with `car_id` = 999 | 409 (FK) |
| Stop PostgreSQL, call any endpoint | 503 |

SQL injection check:
```bash
curl "http://127.0.0.1:5000/users?name=x'%20OR%20'1'='1"      # returns [] — treated as plain text
curl "http://127.0.0.1:5000/cars?status=available';DROP%20TABLE%20cars;--"   # returns [] — table still exists
```

## 6. Load test
```bash
python load_test.py     # 20 concurrent requests, then prints pool stats from /health
```
