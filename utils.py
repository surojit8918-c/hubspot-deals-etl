import json
import decimal
import uuid
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional


def make_json_serializable(obj):
    """Convert objects to JSON-serializable format with proper key-value structure"""
    if obj is None:
        return None
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, (int, float)):
        return obj
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(key): make_json_serializable(value) for key, value in obj.items()}
    elif hasattr(obj, '__dict__'):
        # Handle objects with attributes - convert to proper key-value dict
        try:
            return {str(k): make_json_serializable(v) for k, v in obj.__dict__.items()}
        except:
            return str(obj)
    else:
        return str(obj)


def deep_serialize(data):
    """Recursively serialize nested data structures ensuring proper JSON key-value format"""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Ensure keys are strings
            str_key = str(key)
            # Recursively serialize values
            result[str_key] = deep_serialize(value)
        return result
    elif isinstance(data, (list, tuple)):
        return [deep_serialize(item) for item in data]
    else:
        return make_json_serializable(data)


def build_dataset_name(organization_id: str, prefix: str = "hubspot_users") -> str:
    """Build a dataset name from organization ID"""
    return f"{prefix}_{organization_id.replace('-', '_')}"


def calculate_duration(start_time_str: str, end_time_str: str) -> Optional[float]:
    """Calculate duration between two ISO datetime strings in seconds"""
    try:
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        duration = end_time - start_time
        return duration.total_seconds()
    except Exception:
        return None


def enhance_filters_with_metadata(filters: Dict[str, Any], scan_id: str) -> Dict[str, Any]:
    """Add scan metadata to filters"""
    return {
        **filters,
        'scan_id': scan_id,
    }


def build_dlt_env_vars(config: Dict[str, Any]) -> Dict[str, str]:
    """Build DLT environment variables from config"""
    return {
        'DESTINATION__POSTGRES__CREDENTIALS__DATABASE': config.get('db_name', 'hubspot_data'),
        'DESTINATION__POSTGRES__CREDENTIALS__USERNAME': config.get('db_user', 'postgres'),
        'DESTINATION__POSTGRES__CREDENTIALS__PASSWORD': config.get('db_password', ''),
        'DESTINATION__POSTGRES__CREDENTIALS__HOST': config.get('db_host', 'localhost'),
        'DESTINATION__POSTGRES__CREDENTIALS__PORT': str(config.get('db_port', 5432)),
    }


def build_sql_queries(dataset_name: str, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, str]:
    """Build SQL queries for data retrieval"""
    full_table_name = f'"{dataset_name}"."{table_name}"'
    
    return {
        'count': f"SELECT COUNT(*) as total FROM {full_table_name}",
        'data': f"""
            SELECT * FROM {full_table_name}
            ORDER BY "_extracted_at" DESC, "id"
            LIMIT {limit} OFFSET {offset}
        """,
        'columns_schema': f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = '{dataset_name}' 
            AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """,
        'columns_structure': f'SELECT * FROM {full_table_name} LIMIT 0',
        'tables_list': f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{dataset_name}'
            AND table_name NOT LIKE '_dlt%'
        """
    }


def convert_db_rows_to_dicts(rows: List[tuple], columns: List[str]) -> List[Dict[str, Any]]:
    """Convert database rows to dictionary format with proper JSON serialization"""
    result = []
    for row in rows:
        if columns and len(columns) > 0:
            # Convert row to proper JSON key-value object with real column names
            row_dict = {}
            for i, value in enumerate(row):
                if i < len(columns):
                    col_name = columns[i]
                    # Clean up column names (remove quotes, etc.)
                    col_name = col_name.strip('"').strip("'")
                else:
                    col_name = f"additional_field_{i}"
                # Ensure proper JSON serialization
                serialized_value = make_json_serializable(value)
                row_dict[col_name] = serialized_value
            result.append(row_dict)
        else:
            # Fallback - create basic structure
            row_dict = {}
            for i, value in enumerate(row):
                row_dict[f"field_{i}"] = make_json_serializable(value)
            result.append(row_dict)
    
    return result


def extract_columns_from_result(result, fallback_columns: List[str] = None) -> List[str]:
    """Extract column names from database result"""
    columns = []
    
    if hasattr(result, 'description') and result.description:
        columns = [desc[0] for desc in result.description]
        if columns:
            return columns
    
    return fallback_columns


def build_pagination_info(total_count: int, limit: int, offset: int) -> Dict[str, Any]:
    """Build pagination information"""
    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "hasMore": offset + limit < total_count,
        "totalPages": max(1, (total_count + limit - 1) // limit) if total_count > 0 else 0
    }