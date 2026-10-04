"""
Swagger/OpenAPI schema definitions for HubSpot User Extraction API
"""
from flask_restx import fields, Api

def register_models(api: Api):
    """Register all API models with the Flask-RESTX Api instance"""
    
    # Authentication model
    auth_model = api.model('Auth', {
        'accessToken': fields.String(
            required=True, 
            description='API access token for authentication', 
        )
    })

    # Date range model
    date_range_model = api.model('DateRange', {
        'startDate': fields.String(
            description='Start date (YYYY-MM-DD)', 
            example='2024-01-01'
        ),
        'endDate': fields.String(
            description='End date (YYYY-MM-DD)',
            example='2024-12-31'
        )
    })

    # Filters model
    filters_model = api.model('Filters', {
        'properties': fields.List(
            fields.String, 
            description='User properties to extract',
            example=['id', 'email', 'firstName', 'lastName', 'roleId', 'createdAt']
        ),
        'includeArchived': fields.Boolean(
            description='Include archived users',
            default=False,
            example=False
        ),
        'dateRange': fields.Nested(date_range_model, description='Date range filter')
    })

    # Scan configuration model
    scan_config_model = api.model('ScanConfig', {
        'scanId': fields.String(
            required=True, 
            description='Unique identifier for the scan',
            example='hubspot-users-scan-2025-001'
        ),
        'organizationId': fields.String(
            required=True, 
            description='Organization identifier',
            example='org-12345'
        ),
        'type': fields.List(
            fields.String, 
            required=True,
            description='Type of scan (must be "user")',
            example=['user']
        ),
        'auth': fields.Nested(auth_model, required=True),
        'filters': fields.Nested(filters_model, description='Scan filters')
    })

    # Scan request model
    scan_request_model = api.model('ScanRequest', {
        'config': fields.Nested(scan_config_model, required=True)
    })

    # Checkpoint info model
    checkpoint_info_model = api.model('CheckpointInfo', {
        'latestCheckpoint': fields.Raw(description='Latest checkpoint data'),
        'progress': fields.Float(description='Progress percentage if available'),
        'lastCheckpointAt': fields.String(description='When last checkpoint was created')
    })

    # Scan status model
    scan_status_model = api.model('ScanStatus', {
        'scanId': fields.String(description='Scan identifier'),
        'organizationId': fields.String(description='Organization identifier'),
        'type': fields.String(description='Scan type'),
        'status': fields.String(
            description='Scan status', 
            enum=['pending', 'running', 'completed', 'failed', 'cancelled', 'crashed', 'resuming']
        ),
        'startTime': fields.String(description='Scan start time (ISO format)'),
        'endTime': fields.String(description='Scan end time (ISO format)'),
        'lastHeartbeat': fields.String(description='Last heartbeat timestamp'),
        'recordsExtracted': fields.Integer(description='Number of records extracted'),
        'duration': fields.Float(description='Scan duration in seconds'),
        'errorMessage': fields.String(description='Error message if failed'),
        'metadata': fields.Raw(description='Additional scan metadata'),
        'config': fields.Raw(description='Scan configuration'),
        'checkpointInfo': fields.Nested(checkpoint_info_model, description='Checkpoint information if available')
    })

    # Pagination model
    pagination_model = api.model('Pagination', {
        'total': fields.Integer(description='Total number of items'),
        'limit': fields.Integer(description='Items per page'),
        'offset': fields.Integer(description='Offset from start'),
        'hasMore': fields.Boolean(description='Whether more items exist'),
        'totalPages': fields.Integer(description='Total number of pages'),
        'returned': fields.Integer(description='Number of items returned in this response')
    })

    # Scan list model
    scan_list_model = api.model('ScanList', {
        'scans': fields.List(fields.Nested(scan_status_model)),
        'pagination': fields.Nested(pagination_model)
    })

    # User property model
    user_property_model = api.model('UserProperty', {
        'name': fields.String(description='Property name'),
        'label': fields.String(description='Property label'),
        'type': fields.String(description='Property type'),
        'description': fields.String(description='Property description')
    })

    # User properties model
    user_properties_model = api.model('UserProperties', {
        'standard': fields.List(fields.Nested(user_property_model)),
        'filters': fields.Raw(description='Available filters')
    })

    # Table info model
    table_info_model = api.model('TableInfo', {
        'name': fields.String(description='Table name'),
        'rowCount': fields.Integer(description='Current row count in database'),
        'extractedCount': fields.Integer(description='Number of records extracted during scan')
    })

    # Tables response model
    tables_response_model = api.model('TablesResponse', {
        'scanId': fields.String(description='Scan identifier'),
        'datasetName': fields.String(description='Database dataset name'),
        'tables': fields.List(fields.Nested(table_info_model)),
        'totalTables': fields.Integer(description='Total number of tables')
    })

    # Results response model
    results_response_model = api.model('ResultsResponse', {
        'scanId': fields.String(description='Scan identifier'),
        'tableName': fields.String(description='Table name'),
        'records': fields.List(fields.Raw, description='Array of data records'),
        'pagination': fields.Nested(pagination_model),
        'availableTables': fields.List(fields.String, description='Available table names'),
        'columns': fields.List(fields.String, description='Column names in the table')
    })

    # Pipeline info model
    pipeline_info_model = api.model('PipelineInfo', {
        'pipeline_name': fields.String(description='Pipeline name'),
        'destination_type': fields.String(description='Destination type'),
        'working_dir': fields.String(description='Working directory'),
        'dataset_name': fields.String(description='Dataset name'),
        'is_active': fields.Boolean(description='Whether pipeline is active'),
        'source_type': fields.String(description='Source type'),
        'uses_api_service': fields.Boolean(description='Whether using API service'),
        'configuration_method': fields.String(description='Configuration method'),
        'database_health': fields.Boolean(description='Database health status'),
        'supports_checkpoints': fields.Boolean(description='Whether checkpoints are supported'),
        'error': fields.String(description='Error message if any')
    })

    # Cleanup request model
    cleanup_request_model = api.model('CleanupRequest', {
        'daysOld': fields.Integer(
            description='Remove scans older than this many days',
            default=7,
            min=1,
            max=365,
            example=7
        )
    })

    # Cleanup response model
    cleanup_response_model = api.model('CleanupResponse', {
        'cleanedCount': fields.Integer(description='Number of scans cleaned up'),
        'daysOld': fields.Integer(description='Days old threshold used')
    })

    # Generic API response model
    api_response_model = api.model('APIResponse', {
        'success': fields.Boolean(description='Whether the request was successful'),
        'message': fields.String(description='Response message'),
        'error': fields.String(description='Error message if failed'),
        'data': fields.Raw(description='Response data')
    })

    # Health model
    health_model = api.model('Health', {
        'status': fields.String(description='Service status', enum=['healthy', 'degraded', 'unhealthy']),
        'timestamp': fields.String(description='Timestamp'),
        'service': fields.String(description='Service name'),
        'environment': fields.String(description='Environment (development, staging, production)'),
        'version': fields.String(description='API version'),
        'pipeline': fields.Nested(pipeline_info_model, description='Pipeline information'),
        'database_health': fields.Raw(description='Detailed database health information'),
        'database_info': fields.Raw(description='Database connection information'),
        'config': fields.Raw(description='Service configuration summary'),
        'issues': fields.List(fields.String, description='List of current issues'),
        'error': fields.String(description='Error message if unhealthy')
    })

    # Statistics model
    statistics_model = api.model('Statistics', {
        'total_jobs': fields.Integer(description='Total number of jobs'),
        'status_breakdown': fields.Raw(description='Job count by status'),
        'recent_jobs_7_days': fields.Integer(description='Recent jobs in last 7 days'),
        'total_records_extracted': fields.Integer(description='Total records extracted across all jobs'),
        'organization_filter': fields.String(description='Organization filter applied'),
        'generated_at': fields.String(description='When statistics were generated')
    })

    # Return models for use in routes
    return {
        'auth_model': auth_model,
        'date_range_model': date_range_model,
        'filters_model': filters_model,
        'scan_config_model': scan_config_model,
        'scan_request_model': scan_request_model,
        'scan_status_model': scan_status_model,
        'checkpoint_info_model': checkpoint_info_model,
        'pagination_model': pagination_model,
        'scan_list_model': scan_list_model,
        'user_property_model': user_property_model,
        'user_properties_model': user_properties_model,
        'table_info_model': table_info_model,
        'tables_response_model': tables_response_model,
        'results_response_model': results_response_model,
        'pipeline_info_model': pipeline_info_model,
        'cleanup_request_model': cleanup_request_model,
        'cleanup_response_model': cleanup_response_model,
        'api_response_model': api_response_model,
        'health_model': health_model,
        'statistics_model': statistics_model
    }