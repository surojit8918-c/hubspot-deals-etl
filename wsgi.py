"""
WSGI entry point for production deployment
"""

import os
from app import create_app

# Create app instance for production
config_name = os.environ.get('FLASK_ENV', 'production')
app = create_app(config_name)

if __name__ == "__main__":
    app.run()