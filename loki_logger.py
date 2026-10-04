"""
Loki logging configuration for Data Extraction Service
"""
import logging
import json
import os
from datetime import datetime
from config import get_config

class LokiJSONFormatter(logging.Formatter):
    """JSON formatter optimized for Loki ingestion with dynamic field support"""

    def __init__(self):
        super().__init__()
        self.config = get_config()

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'service': self.config.DLT_PIPELINE_NAME,
            'environment': os.getenv('FLASK_ENV', 'development'),
            'version': self.config.APP_VERSION
        }

        # Add all custom fields dynamically from the log record
        # This will include any extra fields passed via the 'extra' parameter
        reserved_attributes = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
            'processName', 'process', 'getMessage', 'extra'
        }
        
        # Add any additional attributes that aren't standard LogRecord attributes
        for key, value in record.__dict__.items():
            if key not in reserved_attributes and not key.startswith('_'):
                # Handle potential serialization issues with complex objects
                try:
                    # Test if the value is JSON serializable
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    # Convert non-serializable objects to string
                    log_data[key] = str(value)

        # Add exception details if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_data, ensure_ascii=False)


def get_log_level_for_env():
    """Get appropriate log level based on environment"""
    config = get_config()
    
    # Use config's LOG_LEVEL if available, otherwise fallback to environment defaults
    if hasattr(config, 'LOG_LEVEL'):
        return getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    
    env = os.getenv('FLASK_ENV', 'development').lower()
    log_levels = {
        'development': logging.DEBUG,    # Show everything for debugging
        'testing': logging.WARNING,      # Reduce noise during tests
        'staging': logging.INFO,         # Normal operations
        'production': logging.INFO       # Changed from WARNING to INFO for better observability
    }

    return log_levels.get(env, logging.INFO)


def setup_loki_logging():
    """Setup logging configuration for Loki integration"""
    config = get_config()

    # Get log directory from config or environment
    log_dir = os.path.dirname(config.LOG_FILE_PATH) if hasattr(config, 'LOG_FILE_PATH') else '/app/logs'
    log_file = os.path.basename(config.LOG_FILE_PATH) if hasattr(config, 'LOG_FILE_PATH') else 'app.jsonl'
    log_format = os.getenv('LOG_FORMAT', 'json').lower()

    # Ensure logs directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Get environment-specific log level
    env_log_level = get_log_level_for_env()
    env = os.getenv('FLASK_ENV', 'development').lower()

    # Create JSON formatter for both console and file
    json_formatter = LokiJSONFormatter()

    # Create fallback formatter for when JSON is disabled
    if log_format != 'json':
        # Fallback to standard formatter if JSON is not desired
        standard_formatter = logging.Formatter(
            config.LOG_FORMAT if hasattr(config, 'LOG_FORMAT') else '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        console_formatter = standard_formatter
        file_formatter = standard_formatter
    else:
        # Use JSON for both console and file
        console_formatter = json_formatter
        file_formatter = json_formatter

    # File handler for logs (always DEBUG level for complete logging)
    log_file_path = os.path.join(log_dir, log_file)

    # Use RotatingFileHandler to prevent log files from growing too large
    from logging.handlers import RotatingFileHandler
    max_bytes = getattr(config, 'LOG_MAX_BYTES', 10485760)  # 10MB default
    backup_count = getattr(config, 'LOG_BACKUP_COUNT', 5)

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # Always capture everything to file

    # Console handler - same format as file, environment-specific level
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(env_log_level)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Root level always DEBUG
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Third-party library log levels (environment-specific)
    third_party_loggers = {
        'werkzeug': logging.WARNING,
        'urllib3': logging.WARNING,
        'requests': logging.INFO,
        'sqlalchemy.engine': logging.WARNING,
        'azure': logging.INFO,
        'msal': logging.INFO,
        'docker': logging.WARNING,
        'redis': logging.WARNING
    }

    if env == 'production':
        # Silence most third-party logs in production
        for logger_name in third_party_loggers:
            logging.getLogger(logger_name).setLevel(logging.ERROR)
    else:
        # Use configured levels for dev/test/staging
        for logger_name, level in third_party_loggers.items():
            logging.getLogger(logger_name).setLevel(level)

    # Log the configuration
    setup_logger = logging.getLogger(__name__)
    setup_logger.info(
        f"Logging configured for {env} environment",
        extra={
            'operation': 'logging_setup',
            'environment': env,
            'console_level': logging.getLevelName(env_log_level),
            'file_level': 'DEBUG',
            'log_file': log_file_path,
            'log_format': log_format,
            'max_bytes': max_bytes,
            'backup_count': backup_count,
            'console_format': 'JSON' if log_format == 'json' else 'STANDARD',
            'file_format': 'JSON' if log_format == 'json' else 'STANDARD'
        }
    )

    return root_logger


def get_logger(name):
    """Get a logger with consistent configuration"""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        setup_loki_logging()
    return logging.getLogger(name)


def log_performance(operation_name):
    """Decorator for logging performance metrics"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = datetime.utcnow()

            try:
                result = func(*args, **kwargs)
                end_time = datetime.utcnow()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                logger.info(
                    f"Performance: {operation_name} completed",
                    extra={
                        'operation': operation_name,
                        'duration_ms': round(duration_ms, 2),
                        'function': func.__name__,
                        'status': 'success'
                    }
                )

                return result

            except Exception as e:
                end_time = datetime.utcnow()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                logger.error(
                    f"Performance: {operation_name} failed",
                    extra={
                        'operation': operation_name,
                        'duration_ms': round(duration_ms, 2),
                        'function': func.__name__,
                        'status': 'error',
                        'error': str(e)
                    },
                    exc_info=True
                )
                raise

        return wrapper
    return decorator


class ContextLogger:
    """Context manager for adding consistent logging context"""

    def __init__(self, logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)

# Utility functions for common logging patterns


def log_request_start(logger, request_id, operation, **extra_context):
    """Log the start of a request/operation"""
    logger.info(
        f"Starting {operation}",
        extra={
            'request_id': request_id,
            'operation': f"{operation}_start",
            'phase': 'start',
            **extra_context
        }
    )


def log_request_end(logger, request_id, operation, duration_ms=None, **extra_context):
    """Log the end of a request/operation"""
    extra = {
        'request_id': request_id,
        'operation': f"{operation}_end",
        'phase': 'end',
        **extra_context
    }

    if duration_ms is not None:
        extra['duration_ms'] = duration_ms

    logger.info(
        f"Completed {operation}",
        extra=extra
    )


def log_business_event(logger, event_name, **context):
    """Log important business events"""
    logger.info(
        f"Business Event: {event_name}",
        extra={
            'operation': 'business_event',
            'event_name': event_name,
            'event_type': 'business',
            **context
        }
    )


def log_security_event(logger, event_name, severity='INFO', **context):
    """Log security-related events"""
    log_level = getattr(logging, severity.upper(), logging.INFO)

    logger.log(
        log_level,
        f"Security Event: {event_name}",
        extra={
            'operation': 'security_event',
            'event_name': event_name,
            'event_type': 'security',
            'severity': severity,
            **context
        }
    )


def log_api_call(logger, api_name, method='GET', status_code=None, duration_ms=None, **context):
    """Log external API calls"""
    extra = {
        'operation': 'api_call',
        'api_name': api_name,
        'api_method': method,
        **context
    }

    if status_code is not None:
        extra['api_status_code'] = status_code
    if duration_ms is not None:
        extra['api_duration_ms'] = duration_ms

    if status_code and status_code >= 400:
        logger.warning(f"API call failed: {api_name}", extra=extra)
    else:
        logger.info(f"API call: {api_name}", extra=extra)


def configure_app_logging(app):
    # Guard against multiple registrations
    if hasattr(app, '_logging_configured'):
        return app.logger
    app._logging_configured = True
    """Configure Flask app-specific logging with request/response hooks"""
    config = get_config()

    # Set app logger level based on config
    app.logger.setLevel(get_log_level_for_env())

    # Add request/response logging hooks
    @app.before_request
    def log_request_start():
        """Log incoming request details"""
        from flask import request, g
        import uuid
        
        # Generate or extract request ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        g.request_id = request_id
        g.start_time = datetime.utcnow()
        
        logger = get_logger('app.request')
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'request_id': request_id,
                'operation': 'request_start',
                'debug_process': 'request_lifecycle',
                'debug_step': 'request_received',
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'content_type': request.content_type,
                'content_length': request.content_length,
                'query_params': dict(request.args),
                'endpoint': request.endpoint
            }
        )

    @app.after_request
    def log_request_end(response):
        """Log response details"""
        from flask import request, g
        
        request_id = getattr(g, 'request_id', 'unknown')
        start_time = getattr(g, 'start_time', datetime.utcnow())
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger = get_logger('app.request')
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        # Safely get response size
        response_size = 0
        try:
            # Only try to get data if response is not in direct passthrough mode
            if hasattr(response, 'direct_passthrough') and response.direct_passthrough:
                response_size = 'passthrough'
            else:
                response_data = response.get_data()
                if response_data:
                    response_size = len(response_data)
        except (RuntimeError, Exception):
            # If we can't get response data safely, just set to unknown
            response_size = 'unknown'
            
        logger.log(
            log_level,
            f"Request completed: {request.method} {request.path} - {response.status_code}",
            extra={
                'request_id': request_id,
                'operation': 'request_end',
                'debug_process': 'request_lifecycle',
                'debug_step': 'response_sent',
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2),
                'response_size': response_size,
                'content_type': response.content_type,
                'endpoint': request.endpoint
            }
        )
        
        return response

    @app.teardown_request
    def log_request_teardown(exception):
        """Log request teardown and any exceptions"""
        from flask import request, g
        
        request_id = getattr(g, 'request_id', 'unknown')
        
        if exception:
            logger = get_logger('app.request')
            logger.error(
                f"Request failed with exception: {request.method} {request.path}",
                extra={
                    'request_id': request_id,
                    'operation': 'request_exception',
                    'debug_process': 'request_lifecycle',
                    'debug_step': 'request_teardown_exception',
                    'method': request.method,
                    'path': request.path,
                    'exception_type': type(exception).__name__,
                    'error': str(exception)
                },
                exc_info=True
            )

    # Add error handlers for different HTTP error codes
    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors"""
        from flask import request, g
        
        request_id = getattr(g, 'request_id', 'unknown')
        logger = get_logger('app.error')
        
        logger.warning(
            f"Bad Request: {request.method} {request.path}",
            extra={
                'request_id': request_id,
                'operation': 'error_400',
                'debug_process': 'error_handling',
                'debug_step': 'bad_request',
                'method': request.method,
                'path': request.path,
                'error_code': 400,
                'error_description': str(error.description)
            }
        )
        
        return {
            'error': 'Bad Request',
            'message': error.description or 'Invalid request'
        }, 400

    @app.errorhandler(401)
    def handle_unauthorized(error):
        """Handle 401 Unauthorized errors"""
        from flask import request, g
        
        request_id = getattr(g, 'request_id', 'unknown')
        logger = get_logger('app.error')
        
        logger.warning(
            f"Unauthorized: {request.method} {request.path}",
            extra={
                'request_id': request_id,
                'operation': 'error_401',
                'debug_process': 'error_handling',
                'debug_step': 'unauthorized',
                'method': request.method,
                'path': request.path,
                'error_code': 401,
                'remote_addr': request.remote_addr
            }
        )
        
        return {
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }, 401

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors"""
        from flask import request, g
        
        request_id = getattr(g, 'request_id', 'unknown')
        logger = get_logger('app.error')
        
        logger.info(
            f"Not Found: {request.method} {request.path}",
            extra={
                'request_id': request_id,
                'operation': 'error_404',
                'debug_process': 'error_handling',
                'debug_step': 'not_found',
                'method': request.method,
                'path': request.path,
                'error_code': 404,
                'remote_addr': request.remote_addr
            }
        )
        
        return {
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }, 404

    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle 429 Too Many Requests errors"""
        from flask import request, g
        
        request_id = getattr(g, 'request_id', 'unknown')
        logger = get_logger('app.error')
        
        logger.warning(
            f"Rate Limited: {request.method} {request.path}",
            extra={
                'request_id': request_id,
                'operation': 'error_429',
                'debug_process': 'error_handling',
                'debug_step': 'rate_limited',
                'method': request.method,
                'path': request.path,
                'error_code': 429,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')
            }
        )
        
        return {
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later.'
        }, 429

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server Error"""
        from flask import request, g
        
        request_id = getattr(g, 'request_id', 'unknown')
        logger = get_logger('app.error')
        
        logger.error(
            f"Internal Server Error: {request.method} {request.path}",
            extra={
                'request_id': request_id,
                'operation': 'error_500',
                'debug_process': 'error_handling',
                'debug_step': 'internal_error',
                'method': request.method,
                'path': request.path,
                'error_code': 500,
                'error_description': str(error) if error else 'Unknown internal error'
            },
            exc_info=True
        )
        
        return {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }, 500

    # Log successful app configuration
    logger = get_logger(__name__)
    logger.info(
        "Flask app logging configured with request/response hooks",
        extra={
            'operation': 'app_logging_setup',
            'debug_process': 'app_initialization',
            'debug_step': 'logging_hooks_configured',
            'hooks_added': ['before_request', 'after_request', 'teardown_request'],
            'error_handlers_added': [400, 401, 404, 429, 500],
            'service': config.DLT_PIPELINE_NAME,
            'environment': os.getenv('FLASK_ENV', 'development')
        }
    )

    return app.logger