# This file can be simplified or removed since database.py handles everything
from .database import get_db_session, get_db_session_scope, init_database, check_database_health

# Alias for backward compatibility
get_db = get_db_session
init_db = init_database