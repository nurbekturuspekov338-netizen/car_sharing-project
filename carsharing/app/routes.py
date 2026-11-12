"""REST endpoints. Every query is parameterised (%s) -> no SQL injection."""
from flask import Blueprint, jsonify, request

from .db import get_pool, serializable, transaction, with_retry
from .errors import ApiError

bp = Blueprint("api", __name__)


def _body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("JSON object body required", 400)
    return data


# ---------------------------------------------------------------- users
@bp.get("/users")
def list_users():
    name = request.args.get("name")                       # optional search ?name=ar
    pattern = f"%{name}%" if name else None
    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT user_id, user_name, email, date_of_birth, phone_number
               FROM users
               WHERE (%s::text IS NULL OR user_name ILIKE %s::text)
               ORDER BY user_id""",
            (pattern, pattern),
        ).fetchall()
    return jsonify(rows)


@bp.post("/users")
def create_user():
    d = _body()
    with transaction() as conn:
        row = conn.execute(
            """INSERT INTO users (user_name, email, date_of_birth, phone_number)
               VALUES (%s, %s, %s, %s) RETURNING user_id""",
            (d["user_name"], d["email"], d["date_of_birth"], d["phone_number"]),
        ).fetchone()
    return jsonify({"user_id": row["user_id"]}), 201


@bp.put("/users/<int:user_id>")
def update_user(user_id):
    d = _body()
    with transaction() as conn:
        cur = conn.execute(
            """UPDATE users SET user_name = %s, email = %s, phone_number = %s
               WHERE user_id = %s""",
            (d["user_name"], d["email"], d["phone_number"], user_id),
        )
        if cur.rowcount == 0:
            raise ApiError("User not found", 404)
    return jsonify({"updated": user_id})


@bp.delete("/users/<int:user_id>")
def delete_user(user_id):
    with transaction() as conn:
        cur = conn.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        if cur.rowcount == 0:
            raise ApiError("User not found", 404)
    return jsonify({"deleted": user_id})


# ---------------------------------------------------------------- cars
@bp.get("/cars")
def list_cars():
    status = request.args.get("status")                   # ?status=available
    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT car_id, plate_number, brand, model, year, price_per_hour, status
               FROM cars
               WHERE (%s::text IS NULL OR status = %s::text)
               ORDER BY car_id""",
            (status, status),
        ).fetchall()
    return jsonify(rows)


# ---------------------------------------------------------------- rentals
@bp.get("/rentals")
def list_rentals():
    user_id = request.args.get("user_id", type=int)
    status = request.args.get("status")
    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT r.rental_id, r.user_id, r.car_id, c.plate_number,
                      r.start_time, r.end_time, r.price, r.status
               FROM rentals r JOIN cars c ON c.car_id = r.car_id
               WHERE (%s::int  IS NULL OR r.user_id = %s::int)
                 AND (%s::text IS NULL OR r.status  = %s::text)
               ORDER BY r.rental_id""",
            (user_id, user_id, status, status),
        ).fetchall()
    return jsonify(rows)


@bp.post("/rentals")
def create_rental():
    """Start a rental. SERIALIZABLE + retry: two users cannot take the same car."""
    d = _body()
    user_id, car_id = d["user_id"], d["car_id"]
    start = d.get("start_time")                           # optional, default = now

    def tx():
        with serializable() as conn:
            row = conn.execute(
                """INSERT INTO rentals (user_id, car_id, start_time, status)
                   VALUES (%s, %s, COALESCE(%s::timestamp, localtimestamp), 'active')
                   RETURNING rental_id""",
                (user_id, car_id, start),
            ).fetchone()
            return row["rental_id"]

    return jsonify({"rental_id": with_retry(tx)}), 201


@bp.post("/rentals/<int:rental_id>/finish")
def finish_rental(rental_id):
    """Finish rental: end_time, price (trigger) and payment are written atomically."""
    method = (request.get_json(silent=True) or {}).get("method", "card")

    def tx():
        with serializable() as conn:
            exists = conn.execute(
                "SELECT 1 FROM rentals WHERE rental_id = %s", (rental_id,)).fetchone()
            if exists is None:
                raise ApiError("Rental not found", 404)
            conn.execute("CALL finish_rental(%s::int, %s::varchar)", (rental_id, method))
            return conn.execute(
                "SELECT rental_id, status, end_time, price FROM rentals WHERE rental_id = %s",
                (rental_id,),
            ).fetchone()

    return jsonify(with_retry(tx))


# ---------------------------------------------------------------- payments / reports
@bp.get("/payments")
def list_payments():
    rental_id = request.args.get("rental_id", type=int)
    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT payment_id, rental_id, payment_date, amount, method
               FROM payments
               WHERE (%s::int IS NULL OR rental_id = %s::int)
               ORDER BY payment_id""",
            (rental_id, rental_id),
        ).fetchall()
    return jsonify(rows)


@bp.get("/reports/top-users")
def top_users():
    with get_pool().connection() as conn:
        rows = conn.execute(
            """SELECT user_name, completed_rentals, total_paid,
                      RANK() OVER (ORDER BY total_paid DESC) AS rnk
               FROM v_user_revenue ORDER BY rnk, user_name"""
        ).fetchall()
    return jsonify(rows)


# ---------------------------------------------------------------- health
@bp.get("/health")
def health():
    pool = get_pool()
    try:
        pool.check()
        return jsonify({"status": "ok", "pool": pool.get_stats()})
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "error", "detail": str(e)}), 503
