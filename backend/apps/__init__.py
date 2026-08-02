import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from extensions import db, login_manager


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    max_content_length_mb = int(os.getenv("MAX_CONTENT_LENGTH_MB", "100"))
    app.config["MAX_CONTENT_LENGTH"] = max_content_length_mb * 1024 * 1024
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(_: RequestEntityTooLarge):
        return (
            jsonify(
                {
                    "error": "Request entity too large."
                    f" Increase MAX_CONTENT_LENGTH_MB if you need to upload bigger files.",
                }
            ),
            413,
        )

    cors_origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")
    CORS(app, resources={r"/api/*": {"origins": cors_origin}}, supports_credentials=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Load blueprints
    from routes.auth import auth_bp
    from routes.framework import framework_bp
    from routes.health import health_bp
    from routes.project import project_bp
    from routes.rag import rag_bp
    from routes.report import report_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp
    from routes.field_mapping import field_mapping_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(project_bp, url_prefix="/api/projects")
    app.register_blueprint(framework_bp, url_prefix="/api/frameworks")
    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")
    app.register_blueprint(field_mapping_bp, url_prefix="/api/field-mapping")

    @app.get("/")
    def root():
        return jsonify(
            {
                "name": "DataMind Backend",
                "message": "Backend service is running",
                "health": "/api/health",
                "stt": "/api/stt/transcribe",
                "rag": "/api/rag",
                "gemini": "/api/gemini",
                "mineru": "/api/mineru",
                "field_mapping": "/api/field-mapping",
            }
        )

    return app
