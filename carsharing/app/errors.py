"""Mapping of psycopg3 / PostgreSQL errors to HTTP status codes."""
import psycopg
from flask import jsonify
from psycopg import errors as pg


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def _resp(message: str, status: int):
    return jsonify({"error": message}), status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def api_error(e):
        return _resp(e.message, e.status)

    @app.errorhandler(KeyError)
    def missing_key(e):
        return _resp(f"Missing required field: {e.args[0]}", 400)

    @app.errorhandler(404)
    def not_found(_):
        return _resp("Not found", 404)

    @app.errorhandler(pg.UniqueViolation)
    def unique(e):
        return _resp(f"Duplicate value violates constraint {e.diag.constraint_name}", 409)

    @app.errorhandler(pg.NotNullViolation)
    def not_null(e):
        return _resp(f"Missing required field: {e.diag.column_name}", 400)

    @app.errorhandler(pg.CheckViolation)
    def check(e):
        return _resp(f"Invalid value (constraint {e.diag.constraint_name})", 400)

    @app.errorhandler(pg.ForeignKeyViolation)
    def fk(e):
        return _resp("Referenced record does not exist or is still in use", 409)

    @app.errorhandler(pg.ExclusionViolation)
    def exclusion(e):
        return _resp("The car is already booked/rented for this period", 409)

    @app.errorhandler(pg.RaiseException)       # RAISE EXCEPTION from triggers / procedures
    def raised(e):
        return _resp(e.diag.message_primary, 422)

    @app.errorhandler(pg.DataError)            # bad date / number format etc.
    def data_error(e):
        return _resp("Invalid data format", 400)

    @app.errorhandler(pg.SerializationFailure)  # still failing after all retries
    def serialization(e):
        return _resp("Concurrent update conflict, please retry", 409)

    @app.errorhandler(psycopg.OperationalError)  # DB down, pool timeout (PoolTimeout subclasses it)
    def operational(e):
        return _resp("Database unavailable", 503)
