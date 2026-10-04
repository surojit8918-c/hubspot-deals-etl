import os
from typing import Dict, Any


class Config:
    """Base application configuration"""
    APP_VERSION= os.environ.get('APP_VERSION', '1.0.0')
    APP_TITLE = os.environ.get('APP_TITLE', 'Data Extraction Service')
    APP_DESCRIPTION = os.environ.get('APP_DESCRIPTION', 'Service for extracting and loading data using DLT')

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-immediately')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # Encryption settings
    ENCRYPTION_ENABLED = os.environ.get('ENCRYPTION_ENABLED', 'True').lower() == 'true'
    ENCRYPTION_PASSWORD = os.environ.get('CONFIG_PASSWORD', 'default-password-change-in-production')
    ENCRYPTION_ALGORITHM = os.environ.get('CONFIG_ENCRYPTION_ALGORITHM', 'SHA512')

    # Server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Database settings for DLT PostgreSQL destination
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 5432))
    DB_NAME = os.environ.get('DB_NAME', 'extracted_data')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_SCHEMA = os.environ.get('DB_SCHEMA', 'main')
    
    # Connection pool settings
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 10))
    DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 20))
    DB_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', 30))
    DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))
    
    # DLT specific settings
    DLT_PIPELINE_NAME = os.environ.get('DLT_PIPELINE_NAME', 'data_extraction')
    DLT_WORKING_DIR = os.environ.get('DLT_WORKING_DIR', '.dlt')
    DLT_RUNTIME_ENV = os.environ.get('DLT_RUNTIME_ENV', 'production')
    
    # External API settings
    API_BASE_URL = os.environ.get('API_BASE_URL', 'https://api.example.com')
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 30))
    API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', 100))
    API_USERS_ENDPOINT = os.environ.get('API_USERS_ENDPOINT', '/users')
    API_TEAMS_ENDPOINT = os.environ.get('API_TEAMS_ENDPOINT', '/teams')
    API_RETRY_ATTEMPTS = int(os.environ.get('API_RETRY_ATTEMPTS', 3))
    API_RETRY_DELAY = int(os.environ.get('API_RETRY_DELAY', 1))
    
    # Extraction service settings
    MAX_CONCURRENT_SCANS = int(os.environ.get('MAX_CONCURRENT_SCANS', 5))
    SCAN_TIMEOUT_HOURS = int(os.environ.get('SCAN_TIMEOUT_HOURS', 24))
    CLEANUP_DAYS = int(os.environ.get('CLEANUP_DAYS', 7))
    DEFAULT_BATCH_SIZE = int(os.environ.get('DEFAULT_BATCH_SIZE', 100))
    
    # Cache settings (Redis)
    CACHE_ENABLED = os.environ.get('CACHE_ENABLED', 'True').lower() == 'true'
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'redis')
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', 'json')
    LOG_DATE_FORMAT = os.environ.get('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
    LOG_FILE_PATH = os.environ.get('LOG_FILE_PATH', 'logs/app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Loki logging (optional)
    LOKI_ENABLED = os.environ.get('LOKI_ENABLED', 'False').lower() == 'true'
    LOKI_URL = os.environ.get('LOKI_URL', 'http://localhost:3100')
    LOKI_USERNAME = os.environ.get('LOKI_USERNAME', '')
    LOKI_PASSWORD = os.environ.get('LOKI_PASSWORD', '')
    LOKI_LABELS = {
        'app': 'data_extraction',
        'env': os.environ.get('FLASK_ENV', 'development'),
        'service': 'api'
    }
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With']
    
    # Security settings
    BCRYPT_LOG_ROUNDS = int(os.environ.get('BCRYPT_LOG_ROUNDS', 12))
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'True').lower() == 'true'
    WTF_CSRF_TIME_LIMIT = int(os.environ.get('WTF_CSRF_TIME_LIMIT', 3600))
    
    # Rate limiting
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}')
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    
    # Health check settings
    HEALTH_CHECK_ENABLED = True
    HEALTH_CHECK_DATABASE = True
    HEALTH_CHECK_CACHE = True
    
    # API-specific settings
    API_DOCS_PATH = '/docs'
    API_DOCS_ENABLED = True
    API_PREFIX = '/api'
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get the PostgreSQL database URL for SQLAlchemy/DLT"""
        password_part = f":{cls.DB_PASSWORD}" if cls.DB_PASSWORD else ""
        return f"postgresql://{cls.DB_USER}{password_part}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def get_redis_url(cls) -> str:
        """Get the Redis connection URL"""
        password_part = f":{cls.REDIS_PASSWORD}@" if cls.REDIS_PASSWORD else "@"
        return f"redis://{password_part}{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
    
    @classmethod
    def get_extraction_config(cls) -> Dict[str, Any]:
        """Get configuration for the extraction service"""
        return {
            # Database configuration
            'db_host': cls.DB_HOST,
            'db_port': cls.DB_PORT,
            'db_name': cls.DB_NAME,
            'db_user': cls.DB_USER,
            'db_password': cls.DB_PASSWORD,
            'db_schema': cls.DB_SCHEMA,
            'db_pool_size': cls.DB_POOL_SIZE,
            'db_max_overflow': cls.DB_MAX_OVERFLOW,
            
            # DLT configuration
            'pipeline_name': cls.DLT_PIPELINE_NAME,
            'working_dir': cls.DLT_WORKING_DIR,
            'runtime_env': cls.DLT_RUNTIME_ENV,
            
            # Service configuration
            'max_concurrent_scans': cls.MAX_CONCURRENT_SCANS,
            'scan_timeout_hours': cls.SCAN_TIMEOUT_HOURS,
            'default_batch_size': cls.DEFAULT_BATCH_SIZE,
            
            # External API configuration
            'api_base_url': cls.API_BASE_URL,
            'api_timeout': cls.API_TIMEOUT,
            'api_rate_limit': cls.API_RATE_LIMIT,
            'api_users_endpoint': cls.API_USERS_ENDPOINT,
            'api_teams_endpoint': cls.API_TEAMS_ENDPOINT,
            'api_retry_attempts': cls.API_RETRY_ATTEMPTS,
            'api_retry_delay': cls.API_RETRY_DELAY,
            
            # Cache configuration
            'cache_enabled': cls.CACHE_ENABLED,
            'redis_url': cls.get_redis_url() if cls.CACHE_ENABLED else None,
            'cache_timeout': cls.CACHE_DEFAULT_TIMEOUT
        }
    
    @classmethod
    def get_dlt_config(cls) -> Dict[str, Any]:
        """Get DLT specific configuration"""
        return {
            'destination': {
                'postgres': {
                    'host': cls.DB_HOST,
                    'port': cls.DB_PORT,
                    'database': cls.DB_NAME,
                    'username': cls.DB_USER,
                    'password': cls.DB_PASSWORD,
                    'schema_name': cls.DB_SCHEMA,
                    'connect_timeout': cls.DB_POOL_TIMEOUT
                }
            },
            'runtime': {
                'log_level': cls.LOG_LEVEL,
                'pipeline_name': cls.DLT_PIPELINE_NAME,
                'working_dir': cls.DLT_WORKING_DIR,
                'environment': cls.DLT_RUNTIME_ENV
            },
            'sources': {
                'data_source': {
                    'base_url': cls.API_BASE_URL,
                    'users_endpoint': cls.API_USERS_ENDPOINT,
                    'teams_endpoint': cls.API_TEAMS_ENDPOINT,
                    'batch_size': cls.DEFAULT_BATCH_SIZE,
                    'timeout': cls.API_TIMEOUT,
                    'retry_attempts': cls.API_RETRY_ATTEMPTS
                }
            }
        }
    
    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format': cls.LOG_FORMAT,
                    'datefmt': cls.LOG_DATE_FORMAT
                },
                'json': {
                    '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                    'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': cls.LOG_LEVEL,
                    'formatter': 'default',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': cls.LOG_LEVEL,
                    'formatter': 'json',
                    'filename': cls.LOG_FILE_PATH,
                    'maxBytes': cls.LOG_MAX_BYTES,
                    'backupCount': cls.LOG_BACKUP_COUNT
                }
            },
            'root': {
                'level': cls.LOG_LEVEL,
                'handlers': ['console', 'file']
            },
            'loggers': {
                'dlt': {
                    'level': 'INFO',
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'sqlalchemy': {
                    'level': 'WARNING',
                    'handlers': ['console'],
                    'propagate': False
                },
                'requests': {
                    'level': 'WARNING',
                    'handlers': ['console'],
                    'propagate': False
                }
            }
        }

    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """
        Get API-specific configuration settings.
        This function is useful for passing a clean dictionary of API settings
        to a service or client without including other application-level config.
        """
        return {
            'title': cls.DLT_PIPELINE_NAME,
            'version': cls.APP_VERSION,
            'description': cls.APP_DESCRIPTION,
            'docs_path': cls.API_DOCS_PATH,
            'docs_enabled': cls.API_DOCS_ENABLED,
            'prefix': cls.API_PREFIX,
            'api_base_url': cls.API_BASE_URL,
            'api_timeout': cls.API_TIMEOUT,
            'api_rate_limit': cls.API_RATE_LIMIT,
            'users_endpoint': cls.API_USERS_ENDPOINT,
            'teams_endpoint': cls.API_TEAMS_ENDPOINT,
            'retry_attempts': cls.API_RETRY_ATTEMPTS,
            'retry_delay': cls.API_RETRY_DELAY,
            "max_scan_list_limit": 100,      # Max number of scans to return per page
            "default_scan_list_limit": 20,   # Default number of scans to return per page
            "max_results_limit": 500,        # Max number of scan results (users) per page
            "default_results_limit": 100,    # Default number of results per page            
            # Maintenance and job detection
            "crash_detection_timeout": 10,   # Timeout in minutes to detect crashed jobs
            "max_crash_detection_timeout": 60, # Maximum allowed timeout value for crash detection
        }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Use development database
    DB_NAME = os.environ.get('DB_NAME', 'extracted_data_dev')
    
    # Relaxed settings for development
    MAX_CONCURRENT_SCANS = int(os.environ.get('MAX_CONCURRENT_SCANS', 2))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    
    # Development CORS - more permissive
    CORS_ORIGINS = ['*']  # Allow all origins in development
    
    # Disable rate limiting in development
    RATELIMIT_ENABLED = False
    
    # Development specific settings
    FLASK_ENV = 'development'
    LOKI_ENABLED = os.environ.get('LOKI_ENABLED', 'true').lower() == 'true'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = False
    
    # Use test database
    DB_NAME = os.environ.get('DB_NAME', 'extracted_data_test')
    DB_SCHEMA = os.environ.get('DB_SCHEMA', 'main_test')
    
    # Disable external services in testing
    CACHE_ENABLED = False
    LOKI_ENABLED = False
    RATELIMIT_ENABLED = False
    
    # Fast testing settings
    MAX_CONCURRENT_SCANS = 1
    SCAN_TIMEOUT_HOURS = 1
    DEFAULT_BATCH_SIZE = 10
    
    # Test specific settings
    WTF_CSRF_ENABLED = False
    BCRYPT_LOG_ROUNDS = 4  # Faster for tests


class StagingConfig(Config):
    """Staging configuration"""
    DEBUG = False
    TESTING = False
    
    # Use staging database
    DB_NAME = os.environ.get('DB_NAME', 'extracted_data_staging')
    
    # Production-like settings but with more logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    MAX_CONCURRENT_SCANS = int(os.environ.get('MAX_CONCURRENT_SCANS', 3))
    
    # Enable monitoring
    LOKI_ENABLED = os.environ.get('LOKI_ENABLED', 'True').lower() == 'true'
    
    # Staging specific settings
    FLASK_ENV = 'staging'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production database
    DB_NAME = os.environ.get('DB_NAME', 'extracted_data')
    
    # Strict production settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    MAX_CONCURRENT_SCANS = int(os.environ.get('MAX_CONCURRENT_SCANS', 10))
    
    # Security: These MUST be set in production
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Required
    DB_PASSWORD = os.environ.get('DB_PASSWORD')  # Required
    
    # Production optimizations
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 20))
    DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 40))
    
    # Enable all monitoring in production
    LOKI_ENABLED = os.environ.get('LOKI_ENABLED', 'True').lower() == 'true'
    RATELIMIT_ENABLED = True
    
    # Production specific settings
    FLASK_ENV = 'production'
    
    @classmethod
    def validate_production_config(cls):
        """Validate that required production settings are set"""
        required_vars = ['SECRET_KEY', 'DB_PASSWORD']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables for production: {', '.join(missing_vars)}\n"
                f"Please set these environment variables before starting the application."
            )
        
        # Validate SECRET_KEY strength
        if len(cls.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long in production")
        
        # Validate database connection
        if not cls.DB_PASSWORD:
            raise ValueError("DB_PASSWORD must be set in production")


# Configuration mapping
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """
    Get configuration by name
    
    Args:
        config_name: Configuration name (development, testing, staging, production)
        
    Returns:
        Configuration class instance
    """
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config_by_name.get(config_name, DevelopmentConfig)
    
    # Validate production config if needed
    if config_name == 'production':
        config_class.validate_production_config()
    
    return config_class


def get_database_engine_config() -> Dict[str, Any]:
    """Get SQLAlchemy engine configuration"""
    config = get_config()
    
    return {
        'url': config.get_database_url(),
        'pool_size': config.DB_POOL_SIZE,
        'max_overflow': config.DB_MAX_OVERFLOW,
        'pool_timeout': config.DB_POOL_TIMEOUT,
        'pool_recycle': config.DB_POOL_RECYCLE,
        'pool_pre_ping': True,
        'echo': config.DEBUG and config.LOG_LEVEL == 'DEBUG'
    }