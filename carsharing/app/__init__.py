from datetime import date, datetime
from decimal import Decimal

from dotenv import load_dotenv
from flask import Flask

from . import db
from .errors import register_error_handlers
from .routes import bp


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.json.default = _json_default
    db.init_pool()                      # one pool for the whole application
    app.register_blueprint(bp)
    register_error_handlers(app)
    return app
