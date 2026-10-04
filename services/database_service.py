import logging
from typing import Dict, List, Any, Tuple, Optional
import dlt
from utils import (
    build_sql_queries, 
    convert_db_rows_to_dicts, 
    extract_columns_from_result,
    build_pagination_info,
    deep_serialize
)

class DatabaseService:
    def __init__(self, pipeline_name: str, destination):
        self.pipeline_name = pipeline_name
        self.destination = destination
        self.logger = logging.getLogger(__name__)

    def get_table_columns(self, client, dataset_name: str, table_name: str) -> List[str]:
        """Get column names for a table using multiple methods"""
        columns = []
        queries = build_sql_queries(dataset_name, table_name)
        
        # Method 1: Query information schema
        try:
            schema_result = client.execute_sql(queries['columns_schema'])
            if hasattr(schema_result, 'fetchall'):
                schema_rows = schema_result.fetchall()
            else:
                schema_rows = list(schema_result)
            columns = [row[0] for row in schema_rows]
            
            if columns:
                self.logger.debug(f"Got columns from schema: {columns}")
                return columns
        except Exception as e:
            self.logger.warning(f"Could not get columns from schema: {str(e)}")
        
        # Method 2: Use a LIMIT 0 query to get column structure
        try:
            structure_result = client.execute_sql(queries['columns_structure'])
            columns = extract_columns_from_result(structure_result)
            if columns:
                self.logger.debug(f"Got columns from LIMIT 0 query: {columns}")
                return columns
        except Exception as e:
            self.logger.warning(f"Could not get columns from LIMIT 0 query: {str(e)}")
        

    def execute_count_query(self, client, query: str) -> int:
        """Execute a count query and return the result"""
        try:
            result = client.execute_sql(query)
            if hasattr(result, 'fetchone'):
                count_row = result.fetchone()
                return count_row[0] if count_row else 0
            else:
                result_list = list(result)
                return result_list[0][0] if result_list else 0
        except Exception as e:
            self.logger.warning(f"Error executing count query: {str(e)}")
            return 0

    def execute_data_query(self, client, query: str, columns: List[str]) -> List[Dict[str, Any]]:
        """Execute a data query and return formatted results"""
        try:
            result = client.execute_sql(query)
            
            # If we still don't have columns, try to get from result description
            if not columns:
                columns = extract_columns_from_result(result)
            
            # Convert results to list
            if hasattr(result, 'fetchall'):
                result_rows = result.fetchall()
            else:
                result_rows = list(result)
            
            return convert_db_rows_to_dicts(result_rows, columns)
            
        except Exception as e:
            self.logger.error(f"Error executing data query: {str(e)}")
            return []

    def get_available_tables(self, client, dataset_name: str) -> List[str]:
        """Get list of available tables in dataset"""
        queries = build_sql_queries(dataset_name, "")
        try:
            tables_result = client.execute_sql(queries['tables_list'])
            if hasattr(tables_result, 'fetchall'):
                table_rows = tables_result.fetchall()
            else:
                table_rows = list(tables_result)
            return [row[0] for row in table_rows]
        except Exception as e:
            self.logger.warning(f"Error getting tables: {str(e)}")
            return []

    def get_scan_data(self, dataset_name: str, table_name: str = "users", 
                      limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get scan data with pagination"""
        try:
            # Create a read-only pipeline connection
            pipeline = dlt.pipeline(
                pipeline_name=self.pipeline_name,
                destination=self.destination,
                dataset_name=dataset_name
            )
            
            with pipeline.sql_client() as client:
                queries = build_sql_queries(dataset_name, table_name, limit, offset)
                
                # Get total count
                total_count = self.execute_count_query(client, queries['count'])
                
                # Get column names
                columns = self.get_table_columns(client, dataset_name, table_name)
                
                # Get paginated data
                rows = self.execute_data_query(client, queries['data'], columns)
                
                # Get available tables
                available_tables = self.get_available_tables(client, dataset_name)
                
                return {
                    "success": True,
                    "data": {
                        "tableName": table_name,
                        "records": rows,
                        "pagination": build_pagination_info(total_count, limit, offset),
                        "availableTables": available_tables,
                        "columns": columns
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting scan data: {str(e)}")
            return {"success": False, "message": f"Failed to retrieve scan data: {str(e)}"}

    def get_tables_with_counts(self, dataset_name: str, table_info: Dict[str, int] = None) -> List[Dict[str, Any]]:
        """Get available tables with their row counts"""
        try:
            pipeline = dlt.pipeline(
                pipeline_name=self.pipeline_name,
                destination=self.destination,
                dataset_name=dataset_name
            )
            
            with pipeline.sql_client() as client:
                available_tables = self.get_available_tables(client, dataset_name)
                
                tables = []
                for table_name in available_tables:
                    # Get row count for each table
                    count_query = f'SELECT COUNT(*) FROM "{dataset_name}"."{table_name}"'
                    row_count = self.execute_count_query(client, count_query)
                    
                    tables.append({
                        "name": table_name,
                        "rowCount": row_count,
                        "extractedCount": table_info.get(table_name, row_count) if table_info else row_count
                    })
                
                return tables
                
        except Exception as e:
            self.logger.warning(f"Error getting table list: {str(e)}")
            return [{
                "name": "users",
                "rowCount": 0,
                "extractedCount": 0
            }]

    def get_database_info(self) -> Dict[str, Any]:
        """Get database statistics and health information"""
        try:
            # Use a temporary pipeline to get database connection
            pipeline = dlt.pipeline(
                pipeline_name=self.pipeline_name,
                destination=self.destination
            )
            
            with pipeline.sql_client() as client:
                # Get database size
                try:
                    size_result = client.execute_sql("""
                        SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                               pg_database_size(current_database()) as db_size_bytes
                    """)
                    if hasattr(size_result, 'fetchone'):
                        size_info = size_result.fetchone()
                    else:
                        size_list = list(size_result)
                        size_info = size_list[0] if size_list else None
                except Exception as e:
                    self.logger.warning(f"Error getting database size: {str(e)}")
                    size_info = None
                
                # Get table count
                try:
                    table_result = client.execute_sql("""
                        SELECT COUNT(*) as table_count
                        FROM information_schema.tables 
                        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                    """)
                    if hasattr(table_result, 'fetchone'):
                        table_count = table_result.fetchone()[0]
                    else:
                        table_list = list(table_result)
                        table_count = table_list[0][0] if table_list else 0
                except Exception as e:
                    self.logger.warning(f"Error getting table count: {str(e)}")
                    table_count = 0
                
                # Get schema count
                try:
                    schema_result = client.execute_sql("""
                        SELECT COUNT(DISTINCT table_schema) as schema_count
                        FROM information_schema.tables 
                        WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    """)
                    if hasattr(schema_result, 'fetchone'):
                        schema_count = schema_result.fetchone()[0]
                    else:
                        schema_list = list(schema_result)
                        schema_count = schema_list[0][0] if schema_list else 0
                except Exception as e:
                    self.logger.warning(f"Error getting schema count: {str(e)}")
                    schema_count = 0
                
                # Get list of all tables grouped by schema
                try:
                    all_tables_result = client.execute_sql("""
                        SELECT table_schema, table_name
                        FROM information_schema.tables 
                        WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                        ORDER BY table_schema, table_name
                    """)
                    if hasattr(all_tables_result, 'fetchall'):
                        table_rows = all_tables_result.fetchall()
                    else:
                        table_rows = list(all_tables_result)
                    
                    # Group tables by schema
                    schemas = {}
                    for row in table_rows:
                        schema_name = row[0]
                        table_name = row[1]
                        if schema_name not in schemas:
                            schemas[schema_name] = []
                        schemas[schema_name].append(table_name)
                    
                except Exception as e:
                    self.logger.warning(f"Error getting table list: {str(e)}")
                    schemas = {}
                
                # Get connection info
                try:
                    conn_result = client.execute_sql("""
                        SELECT current_database(), current_user, 
                               inet_server_addr(), inet_server_port()
                    """)
                    if hasattr(conn_result, 'fetchone'):
                        conn_info = conn_result.fetchone()
                    else:
                        conn_list = list(conn_result)
                        conn_info = conn_list[0] if conn_list else None
                except Exception as e:
                    self.logger.warning(f"Error getting connection info: {str(e)}")
                    conn_info = None
            
            return {
                "connected": True,
                "database": conn_info[0] if conn_info else "hubspot_data",
                "user": conn_info[1] if conn_info else "postgres",
                "host": str(conn_info[2]) if conn_info and conn_info[2] else "postgres",
                "port": conn_info[3] if conn_info else 5432,
                "size_pretty": size_info[0] if size_info else "unknown",
                "size_bytes": size_info[1] if size_info else 0,
                "total_tables": table_count,
                "total_schemas": schema_count,
                "schemas": schemas,
                "health_check_passed": True
            }
            
        except Exception as e:
            self.logger.error(f"Error getting database info: {str(e)}")
            return {
                "connected": False,
                "error": str(e),
                "health_check_passed": False,
                "schemas": {}
            }

    def remove_dataset_tables(self, dataset_name: str, scan_id: str) -> int:
            """Remove records for a specific scan from dataset tables"""
            try:
                records_removed = 0
                
                pipeline = dlt.pipeline(
                    pipeline_name=self.pipeline_name,
                    destination=self.destination,
                    dataset_name=dataset_name
                )
                
                with pipeline.sql_client() as client:
                    # Get list of tables in the schema first
                    tables_query = f"""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = '{dataset_name}' 
                        AND table_type = 'BASE TABLE'
                        AND table_name NOT LIKE '_dlt_%'
                    """
                    
                    try:
                        tables_result = client.execute_sql(tables_query)
                        if hasattr(tables_result, 'fetchall'):
                            table_rows = tables_result.fetchall()
                        else:
                            table_rows = list(tables_result)
                        
                        tables = [row[0] for row in table_rows]
                        
                        # Delete records for this scan from each table
                        for table_name in tables:
                            try:
                                # Delete only records belonging to this scan_id
                                delete_query = f"""
                                    DELETE FROM "{dataset_name}"."{table_name}" 
                                    WHERE _scan_id = '{scan_id}'
                                """
                                
                                result = client.execute_sql(delete_query)
                                
                                # Try to get affected row count
                                if hasattr(result, 'rowcount'):
                                    deleted_count = result.rowcount
                                else:
                                    # Fallback: count remaining records to estimate
                                    count_query = f"""
                                        SELECT COUNT(*) FROM "{dataset_name}"."{table_name}"
                                        WHERE _scan_id = '{scan_id}'
                                    """
                                    remaining = client.execute_sql(count_query)
                                    deleted_count = 0 if hasattr(remaining, 'fetchone') and remaining.fetchone()[0] == 0 else 1
                                
                                records_removed += deleted_count
                                self.logger.debug(f"Deleted {deleted_count} records from {dataset_name}.{table_name} for scan {scan_id}")
                                
                            except Exception as e:
                                self.logger.warning(f"Error deleting from table {table_name}: {str(e)}")
                        
                        # Check if any tables are now empty and could be cleaned up
                        for table_name in tables:
                            try:
                                count_query = f'SELECT COUNT(*) FROM "{dataset_name}"."{table_name}"'
                                count_result = client.execute_sql(count_query)
                                if hasattr(count_result, 'fetchone'):
                                    remaining_count = count_result.fetchone()[0]
                                else:
                                    count_list = list(count_result)
                                    remaining_count = count_list[0][0] if count_list else 0
                                
                                if remaining_count == 0:
                                    self.logger.info(f"Table {table_name} is now empty after removing scan {scan_id}")
                                    # Optionally drop empty tables here if desired
                            except Exception as e:
                                self.logger.debug(f"Could not check remaining count for {table_name}: {e}")
                        
                    except Exception as e:
                        self.logger.error(f"Error removing scan data: {str(e)}")
                        
                self.logger.info(f"Removed {records_removed} records for scan {scan_id} from dataset {dataset_name}")
                return records_removed
                
            except Exception as e:
                self.logger.error(f"Error removing scan data for {scan_id} from dataset {dataset_name}: {str(e)}")
                return 0