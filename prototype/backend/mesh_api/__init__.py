from __future__ import annotations

import os

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .controllers.mesh_controller import mesh_controller
from .controllers.status_controller import status_controller
from .errors.error_handlers import register_error_handlers
from .extensions import limiter


def create_application() -> Flask:
    """Flask application factory.

    Centralizes instance creation, CORS enabling, controller (Blueprint)
    registration and global exception handling. This factory pattern eases
    testing and keeps the entry point (app.py) minimal.
    """
    application = Flask(__name__)
    application.wsgi_app = ProxyFix(application.wsgi_app, x_for=1, x_proto=1)

    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000,https://tcc-delaunay-frontend.onrender.com",
        ).split(",")
        if origin.strip()
    ]

    CORS(application, resources={r"/api/*": {"origins": allowed_origins}})

    limiter.init_app(application)

    application.register_blueprint(mesh_controller)
    application.register_blueprint(status_controller)

    register_error_handlers(application)

    return application
