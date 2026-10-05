from datetime import datetime
from flask import Flask
from flask_cors import CORS
import logging
import os

from config import get_config
from api.routes import create_api
from loki_logger import configure_app_logging
from models.database import initialize_database

def create_app(config_name: str = None) -> Flask:
    """Application factory function"""
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Setup CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:8080", "http://localhost:3001"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        },
        r"/docs/*": {
            "origins": ["http://localhost:3000", "http://localhost:8080", "http://localhost:3001"],
            "methods": ["GET"],
            "allow_headers": ["Content-Type"]
        }
    })
    
    # Setup logging
    setup_logging(app, config)

    # Security check for default encryption password
    if config.ENCRYPTION_PASSWORD == 'default-password-change-in-production':
        if not config.TESTING:
            app.logger.warning(
                "SECURITY WARNING: Using default ENCRYPTION_PASSWORD / CONFIG_PASSWORD ('default-password-change-in-production'). "
                "Set CONFIG_PASSWORD in environment / .env for security."
            )

    # Initialize database tables
    initialize_database()
    
    api = create_api()
    # Initialize Flask-RESTX API
    api.init_app(app)
    
    # Root route
    @app.route('/')
    def index():
        return {
            "service": config.APP_TITLE,
            "version": config.APP_VERSION,
            "documentation": config.API_DOCS_PATH,
            "health": "/api/health",
            "endpoints": {
                "start_scan": "POST /api/scan/start",
                "scan_status": "GET /api/scan/{scan_id}/status",
                "pause_scan": "POST /api/scan/{scan_id}/pause",
                "resume_scan": "POST /api/scan/{scan_id}/resume",
                "cancel_scan": "POST /api/scan/{scan_id}/cancel",
                "list_scans": "GET /api/scan/list",
                "pipeline_info": "GET /api/pipeline/info",
                "cleanup": "POST /api/maintenance/cleanup"
            }
        }

    # Root-level health endpoint alias
    @app.route('/health')
    def root_health():
        try:
            from services.extraction_service import ExtractionService
            extraction_service = ExtractionService(config.get_extraction_config())
            pipeline_info = extraction_service.get_pipeline_info()
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": config.DLT_PIPELINE_NAME,
                "pipeline": pipeline_info
            }, 200
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": config.DLT_PIPELINE_NAME,
                "error": str(e)
            }, 500
    
    return app


def setup_logging(app: Flask, config):
    """Setup application logging"""
    
    # Configure basic logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT
    )
    
    # Setup Loki logging if enabled - ONLY ONCE
    if config.LOKI_ENABLED and not hasattr(app, '_loki_configured'):
        try:
            configure_app_logging(app)
            app._loki_configured = True  # Mark as configured
            app.logger.info("Loki logging enabled")
        except Exception as e:
            app.logger.warning(f"Failed to setup Loki logging: {e}")


# Create app instance
app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)
