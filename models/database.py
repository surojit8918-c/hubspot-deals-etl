from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from contextlib import contextmanager
from typing import Generator, Optional
import logging
import time

from config import get_config, get_database_engine_config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection manager with environment-aware configuration"""
    
    def __init__(self, config_name: Optional[str] = None):
        self.config = get_config(config_name)
        self.engine = None
        self.SessionLocal = None
        self._connection_retries = 3
        self._retry_delay = 1.0
        self._initialize()

    def _initialize(self):
        """Initialize database engine and session factory"""
        for attempt in range(self._connection_retries):
            try:
                # Get engine configuration from config
                engine_config = get_database_engine_config()
                
                # Create engine with environment-specific settings
                self.engine = create_engine(
                    engine_config['url'],
                    pool_size=engine_config['pool_size'],
                    max_overflow=engine_config['max_overflow'],
                    pool_timeout=engine_config['pool_timeout'],
                    pool_recycle=engine_config['pool_recycle'],
                    pool_pre_ping=engine_config['pool_pre_ping'],
                    echo=engine_config['echo']
                )
                
                # Test the connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                # Create session factory
                self.SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )
                
                logger.info(
                    f"Database connection initialized successfully "
                    f"(attempt {attempt + 1}/{self._connection_retries})"
                )
                logger.info(f"Connected to: {self.config.DB_HOST}:{self.config.DB_PORT}/{self.config.DB_NAME}")
                logger.info(f"Pool configuration: size={self.config.DB_POOL_SIZE}, max_overflow={self.config.DB_MAX_OVERFLOW}")
                return
                
            except Exception as e:
                logger.error(
                    f"Database connection attempt {attempt + 1}/{self._connection_retries} failed: {str(e)}"
                )
                
                if attempt < self._connection_retries - 1:
                    logger.info(f"Retrying in {self._retry_delay} seconds...")
                    time.sleep(self._retry_delay)
                    self._retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("All database connection attempts failed")
                    raise

    def get_session(self) -> Session:
        """Get a new database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around database operations"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction rolled back: {str(e)}")
            raise
        finally:
            session.close()

    def init_tables(self, drop_existing: bool = False):
        """Create all database tables"""
        try:
            from models.models import Base
            
            if drop_existing:
                logger.warning("Dropping all existing tables...")
                Base.metadata.drop_all(bind=self.engine)
                
            Base.metadata.create_all(bind=self.engine)
            
            # Log table creation info
            table_names = list(Base.metadata.tables.keys())
            logger.info(f"Database tables created successfully: {table_names}")
            
            # In development, log additional info
            if self.config.DEBUG:
                logger.debug(f"Schema: {self.config.DB_SCHEMA}")
                logger.debug(f"Tables created: {len(table_names)}")
                
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

    def health_check(self, detailed: bool = False) -> dict:
        """Check database connection health with optional detailed info"""
        health_info = {
            'healthy': False,
            'timestamp': time.time(),
            'database': self.config.DB_NAME,
            'host': self.config.DB_HOST
        }
        
        try:
            start_time = time.time()
            
            with self.session_scope() as session:
                # Basic connection test
                result = session.execute(text("SELECT 1 as test")).fetchone()
                
                if detailed:
                    # Additional health checks for detailed info
                    health_info.update({
                        'response_time_ms': round((time.time() - start_time) * 1000, 2),
                        'test_query_result': result[0] if result else None,
                        'pool_size': self.engine.pool.size(),
                        'checked_in_connections': self.engine.pool.checkedin(),
                        'checked_out_connections': self.engine.pool.checkedout(),
                        'overflow_connections': self.engine.pool.overflow(),
                        'invalidated_connections': self.engine.pool.invalidated()
                    })
                    
                    # Check if we can access the jobs table
                    try:
                        jobs_count = session.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
                        health_info['jobs_table_accessible'] = True
                        health_info['total_jobs'] = jobs_count
                    except Exception:
                        health_info['jobs_table_accessible'] = False
                        
            health_info['healthy'] = True
            
            if not detailed:
                logger.debug("Database health check passed")
            else:
                logger.info(f"Database health check passed: {health_info}")
                
        except OperationalError as e:
            logger.error(f"Database operational error during health check: {str(e)}")
            health_info['error'] = f"Operational error: {str(e)}"
        except SQLAlchemyError as e:
            logger.error(f"Database SQLAlchemy error during health check: {str(e)}")
            health_info['error'] = f"SQLAlchemy error: {str(e)}"
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            health_info['error'] = str(e)
            
        return health_info

    def get_connection_info(self) -> dict:
        """Get current database connection information"""
        if not self.engine:
            return {'status': 'not_initialized'}
            
        try:
            return {
                'status': 'connected',
                'url': str(self.engine.url).replace(f':{self.config.DB_PASSWORD}@', ':***@'),
                'pool_size': self.engine.pool.size(),
                'pool_timeout': self.config.DB_POOL_TIMEOUT,
                'pool_recycle': self.config.DB_POOL_RECYCLE,
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'echo': self.engine.echo
            }
        except Exception as e:
            logger.error(f"Failed to get connection info: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def close(self):
        """Close database connections and cleanup"""
        try:
            if self.engine:
                self.engine.dispose()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")

    def recreate_engine(self):
        """Recreate the database engine (useful for connection recovery)"""
        logger.info("Recreating database engine...")
        
        # Close existing engine
        if self.engine:
            self.engine.dispose()
            
        # Reset retry delay
        self._retry_delay = 1.0
        
        # Reinitialize
        self._initialize()

    def execute_raw_sql(self, sql: str, params: dict = None) -> any:
        """Execute raw SQL query (use with caution)"""
        if not self.config.DEBUG:
            logger.warning("Raw SQL execution attempted in non-debug environment")
            
        try:
            with self.session_scope() as session:
                result = session.execute(text(sql), params or {})
                return result.fetchall()
        except Exception as e:
            logger.error(f"Raw SQL execution failed: {str(e)}")
            raise


# Global database manager instance - will use environment config
db_manager = None


def get_db_manager(config_name: Optional[str] = None) -> DatabaseManager:
    """Get or create the global database manager instance"""
    global db_manager
    
    if db_manager is None:
        db_manager = DatabaseManager(config_name)
    
    return db_manager


def initialize_database(config_name: Optional[str] = None, drop_existing: bool = False):
    """Initialize the global database manager and create tables"""
    global db_manager
    
    db_manager = DatabaseManager(config_name)
    db_manager.init_tables(drop_existing=drop_existing)
    
    logger.info("Database initialization completed")


# Convenience functions
def get_db_session() -> Session:
    """Get a new database session"""
    return get_db_manager().get_session()


def get_db_session_scope():
    """Get database session with automatic transaction management"""
    return get_db_manager().session_scope()


def init_database(drop_existing: bool = False):
    """Initialize database tables"""
    get_db_manager().init_tables(drop_existing=drop_existing)


def check_database_health(detailed: bool = False) -> dict:
    """Check if database is healthy"""
    return get_db_manager().health_check(detailed=detailed)


def get_database_info() -> dict:
    """Get database connection information"""
    return get_db_manager().get_connection_info()


def close_database():
    """Close database connections"""
    global db_manager
    
    if db_manager:
        db_manager.close()
        db_manager = None


# Context manager for temporary database connections
@contextmanager
def temporary_db_manager(config_name: str) -> Generator[DatabaseManager, None, None]:
    """Create a temporary database manager for specific environment"""
    temp_manager = DatabaseManager(config_name)
    try:
        yield temp_manager
    finally:
        temp_manager.close()