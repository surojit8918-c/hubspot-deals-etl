"""
Flask-RESTX route definitions for Data Extraction API with minimal Loki logging
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from flask_restx import Api, Resource, Namespace
from flask import request, g
from marshmallow import ValidationError
import logging
from datetime import datetime
import uuid

from .swagger_schemas import register_models
from .schemas import (
    validate_scan_request, 
    validate_pagination_params, 
    validate_cleanup_request,
    ScanConfig
)
from services.extraction_service import ExtractionService
from config import get_config
from loki_logger import get_logger, log_business_event, log_security_event


# Initialize logging
logger = get_logger(__name__)
executor = ThreadPoolExecutor(max_workers=4)

def create_api():
    """Create and configure the Flask-RESTX API"""
    config = get_config()
    api_config = config.get_api_config()
    
    api = Api(
        title=config.APP_TITLE,
        version=config.APP_VERSION,
        description=config.APP_DESCRIPTION,
        doc=api_config['docs_path'],
        prefix=api_config['prefix']
    )
    
    models = register_models(api)
    extraction_service = ExtractionService(config.get_extraction_config())
    
    # Create namespaces
    scan_ns = Namespace('scan', description='Scan operations')
    users_ns = Namespace('users', description='User-related operations')
    results_ns = Namespace('results', description='Results retrieval operations')
    pipeline_ns = Namespace('pipeline', description='Pipeline operations')
    maintenance_ns = Namespace('maintenance', description='Maintenance operations')
    
    api.add_namespace(scan_ns)
    api.add_namespace(users_ns)
    api.add_namespace(results_ns)
    api.add_namespace(pipeline_ns)
    api.add_namespace(maintenance_ns)
    
    @scan_ns.route('/start')
    class StartScan(Resource):
        @scan_ns.expect(models['scan_request_model'])
        @scan_ns.response(400, 'Invalid request data')
        @scan_ns.response(409, 'Scan already exists')
        @scan_ns.response(500, 'Internal server error')
        def post(self):
            """Start a new data extraction scan"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                logger.info(
                    "Starting scan request",
                    extra={
                        'request_id': request_id,
                        'operation': 'start_scan',
                        'endpoint': '/scan/start'
                    }
                )
                
                json_data = request.get_json()
                if not json_data:
                    logger.warning("No JSON data provided", extra={'request_id': request_id})
                    return {
                        "success": False,
                        "message": "No JSON data provided",
                        "error": "No JSON data provided"
                    }, 400

                # Validate request
                try:
                    validated_config = validate_scan_request(json_data)
                except ValidationError as err:
                    logger.error(
                        "Validation failed",
                        extra={
                            'request_id': request_id,
                            'validation_errors': err.messages
                        }
                    )
                    return {
                        "success": False,
                        "message": f"Configuration validation failed: {err.messages}",
                        "error": f"Configuration validation failed: {err.messages}",
                        "validation_errors": err.messages
                    }, 400

                scan_config = ScanConfig(
                    scanId=validated_config['scanId'],
                    organizationId=validated_config['organizationId'],
                    type=validated_config['type'],
                    auth=validated_config['auth'],
                    filters=validated_config['filters']
                )

                # Check for existing scan
                existing_scan = extraction_service.get_scan_status(scan_config.scanId)
                if existing_scan:
                    logger.warning(
                        "Duplicate scan attempt",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_config.scanId,
                            'existing_status': existing_scan.get('status')
                        }
                    )
                    return {
                        "success": False,
                        "message": f"A scan with ID '{scan_config.scanId}' already exists",
                        "error": f"A scan with ID '{scan_config.scanId}' already exists"
                    }, 409

                # Start scan
                executor.submit(asyncio.run, extraction_service.start_scan(validated_config))
                
                logger.info(
                    "Scan accepted for processing",
                    extra={
                        'request_id': request_id,
                        'scan_id': scan_config.scanId,
                        'organization_id': scan_config.organizationId
                    }
                )
                
                log_business_event(
                    logger,
                    "scan_creation_accepted",
                    scan_id=scan_config.scanId,
                    organization_id=scan_config.organizationId
                )
                
                return {
                    "success": True,
                    "message": "Scan initialization accepted and is now processing in the background."
                }, 202

            except Exception as e:
                logger.error(
                    "Error in start_scan",
                    extra={'request_id': request_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"An unexpected error occurred: {str(e)}",
                    "error": str(e)
                }, 500

    @scan_ns.route('/<string:scan_id>/status')
    class ScanStatus(Resource):
        @scan_ns.response(404, 'Scan not found')
        @scan_ns.response(500, 'Internal server error')
        def get(self, scan_id):
            """Get the status of a specific scan"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                scan_status = extraction_service.get_scan_status(scan_id)
                
                if not scan_status:
                    logger.warning(
                        "Scan not found",
                        extra={'request_id': request_id, 'scan_id': scan_id}
                    )
                    return {
                        "success": False,
                        "message": f"No scan found with ID: {scan_id}",
                        "error": f"No scan found with ID: {scan_id}"
                    }, 404

                logger.debug(
                    "Scan status retrieved",
                    extra={
                        'request_id': request_id,
                        'scan_id': scan_id,
                        'status': scan_status.get('status')
                    }
                )

                return {"success": True, "data": scan_status}

            except Exception as e:
                logger.error(
                    "Error getting scan status",
                    extra={'request_id': request_id, 'scan_id': scan_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to retrieve scan status: {str(e)}",
                    "error": str(e)
                }, 500

    @scan_ns.route('/<string:scan_id>/cancel')
    class CancelScan(Resource):
        @scan_ns.response(400, 'Cannot cancel scan')
        @scan_ns.response(404, 'Scan not found')
        @scan_ns.response(500, 'Internal server error')
        def post(self, scan_id):
            """Cancel a running scan"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                result = extraction_service.cancel_scan(scan_id)
                
                if result['success']:
                    logger.info(
                        "Scan cancelled",
                        extra={'request_id': request_id, 'scan_id': scan_id}
                    )
                    log_business_event(logger, "scan_cancelled", scan_id=scan_id)
                    return result
                else:
                    logger.warning(
                        "Scan cancellation failed",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_id,
                            'reason': result.get('message')
                        }
                    )
                    return {
                        "success": False,
                        "message": result['message'],
                        "error": result['message']
                    }, 400

            except Exception as e:
                logger.error(
                    "Error cancelling scan",
                    extra={'request_id': request_id, 'scan_id': scan_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to cancel scan: {str(e)}",
                    "error": str(e)
                }, 500

    @scan_ns.route('/list')
    class ListScans(Resource):
        @scan_ns.param('organizationId', 'Filter by organization ID')
        @scan_ns.param('limit', f'Number of results per page (max {api_config["max_scan_list_limit"]})', type=int, default=api_config['default_scan_list_limit'])
        @scan_ns.param('offset', 'Number of results to skip', type=int, default=0)
        def get(self):
            """List all scans with optional filtering and pagination"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                organization_id = request.args.get('organizationId')
                
                # Validate pagination
                try:
                    limit, offset = validate_pagination_params(
                        request.args.get('limit', api_config['default_scan_list_limit']), 
                        request.args.get('offset', 0),
                        max_limit=api_config['max_scan_list_limit']
                    )
                except ValidationError as err:
                    logger.error(
                        "Pagination validation failed",
                        extra={'request_id': request_id, 'validation_errors': err.messages}
                    )
                    return {
                        "success": False,
                        "message": f"Validation error: {err.messages}",
                        "error": f"Validation error: {err.messages}",
                        "validation_errors": err.messages
                    }, 400
                
                scans = extraction_service.list_scans(organization_id, limit, offset)
                total = len(scans) + offset if len(scans) == limit else offset + len(scans)
                
                logger.debug(
                    "Scans listed",
                    extra={
                        'request_id': request_id,
                        'count': len(scans),
                        'organization_id': organization_id
                    }
                )
                
                return {
                    "success": True,
                    "data": {
                        "scans": scans,
                        "pagination": {
                            "total": total,
                            "limit": limit,
                            "offset": offset,
                            "hasMore": len(scans) == limit,
                            "returned": len(scans)
                        }
                    }
                }

            except Exception as e:
                logger.error(
                    "Error listing scans",
                    extra={'request_id': request_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to list scans: {str(e)}",
                    "error": str(e)
                }, 500

    @scan_ns.route('/statistics')
    class ScanStatistics(Resource):
        @scan_ns.param('organizationId', 'Filter statistics by organization ID')
        def get(self):
            """Get scan statistics"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                organization_id = request.args.get('organizationId')
                statistics = extraction_service.get_scan_statistics(organization_id)
                
                logger.debug(
                    "Statistics retrieved",
                    extra={
                        'request_id': request_id,
                        'organization_id': organization_id,
                        'total_scans': statistics.get('total_scans', 0)
                    }
                )
                
                return {"success": True, "data": statistics}

            except Exception as e:
                logger.error(
                    "Error getting statistics",
                    extra={'request_id': request_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to retrieve scan statistics: {str(e)}",
                    "error": str(e)
                }, 500

    @results_ns.route('/<string:scan_id>/tables')
    class GetAvailableTables(Resource):
        @results_ns.response(404, 'Scan not found')
        @results_ns.response(400, 'Scan not completed')
        @results_ns.response(500, 'Internal server error')
        def get(self, scan_id):
            """Get available tables for a completed scan"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                result = extraction_service.get_available_tables(scan_id)
                
                if result['success']:
                    logger.debug(
                        "Tables retrieved",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_id,
                            'table_count': len(result['data'].get('tables', []))
                        }
                    )
                    return {"success": True, "data": result['data']}
                else:
                    status_code = 404 if "not found" in result['message'].lower() else 400
                    logger.warning(
                        "Tables not available",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_id,
                            'reason': result['message']
                        }
                    )
                    return {
                        "success": False,
                        "message": result['message'],
                        "error": result['message']
                    }, status_code

            except Exception as e:
                logger.error(
                    "Error getting available tables",
                    extra={'request_id': request_id, 'scan_id': scan_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to retrieve available tables: {str(e)}",
                    "error": str(e)
                }, 500

    @results_ns.route('/<string:scan_id>/result')
    class GetScanResults(Resource):
        @results_ns.param('tableName', 'Name of the table to query (default: users)', default='users')
        @results_ns.param('limit', f'Number of records per page (max {api_config["max_results_limit"]})', type=int, default=api_config['default_results_limit'])
        @results_ns.param('offset', 'Number of records to skip', type=int, default=0)
        @results_ns.response(404, 'Scan not found')
        @results_ns.response(400, 'Scan not completed or invalid parameters')
        @results_ns.response(500, 'Internal server error')
        def get(self, scan_id):
            """Get scan results with pagination and table selection"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                table_name = request.args.get('tableName', 'users')
                
                # Validate pagination
                try:
                    limit, offset = validate_pagination_params(
                        request.args.get('limit', api_config['default_results_limit']), 
                        request.args.get('offset', 0),
                        max_limit=api_config['max_results_limit']
                    )
                except ValidationError as err:
                    logger.error(
                        "Results pagination validation failed",
                        extra={'request_id': request_id, 'validation_errors': err.messages}
                    )
                    return {
                        "success": False,
                        "message": f"Validation error: {err.messages}",
                        "error": f"Validation error: {err.messages}",
                        "validation_errors": err.messages
                    }, 400
                
                result = extraction_service.get_scan_results(scan_id, table_name, limit, offset)
                
                if result['success']:
                    logger.debug(
                        "Results retrieved",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_id,
                            'table_name': table_name,
                            'count': len(result['data'].get('results', []))
                        }
                    )
                    return {"success": True, "data": result['data']}
                else:
                    status_code = 404 if "not found" in result['message'].lower() else 400
                    logger.warning(
                        "Results not available",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_id,
                            'table_name': table_name,
                            'reason': result['message']
                        }
                    )
                    return {
                        "success": False,
                        "message": result['message'],
                        "error": result['message']
                    }, status_code

            except Exception as e:
                logger.error(
                    "Error getting scan results",
                    extra={
                        'request_id': request_id,
                        'scan_id': scan_id,
                        'table_name': table_name,
                        'error': str(e)
                    },
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to retrieve scan results: {str(e)}",
                    "error": str(e)
                }, 500

    @pipeline_ns.route('/info')
    class PipelineInfo(Resource):
        def get(self):
            """Get information about the DLT pipeline configuration"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                pipeline_info = extraction_service.get_pipeline_info()
                
                logger.debug(
                    "Pipeline info retrieved",
                    extra={
                        'request_id': request_id,
                        'pipeline_name': pipeline_info.get('pipeline_name')
                    }
                )
                
                return {"success": True, "data": pipeline_info}

            except Exception as e:
                logger.error(
                    "Error getting pipeline info",
                    extra={'request_id': request_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to retrieve pipeline information: {str(e)}",
                    "error": str(e)
                }, 500

    @maintenance_ns.route('/cleanup')
    class Cleanup(Resource):
        @maintenance_ns.expect(models['cleanup_request_model'])
        @maintenance_ns.response(400, 'Invalid request data')
        def post(self):
            """Clean up old scan results"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                json_data = request.get_json() or {}
                
                try:
                    days_old = validate_cleanup_request(json_data)
                except ValidationError as err:
                    logger.error(
                        "Cleanup validation failed",
                        extra={'request_id': request_id, 'validation_errors': err.messages}
                    )
                    return {
                        "success": False,
                        "message": f"Validation error: {err.messages}",
                        "error": f"Validation error: {err.messages}",
                        "validation_errors": err.messages
                    }, 400
                
                cleaned_count = extraction_service.cleanup_old_scans(days_old)
                
                logger.info(
                    "Cleanup completed",
                    extra={
                        'request_id': request_id,
                        'cleaned_count': cleaned_count,
                        'days_old': days_old
                    }
                )
                
                log_security_event(
                    logger,
                    "data_cleanup_performed",
                    cleaned_count=cleaned_count,
                    days_old=days_old
                )
                
                return {
                    "success": True,
                    "data": {"cleanedCount": cleaned_count, "daysOld": days_old},
                    "message": f"Successfully cleaned up {cleaned_count} old scan results"
                }

            except Exception as e:
                logger.error(
                    "Error during cleanup",
                    extra={'request_id': request_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to clean up old scans: {str(e)}",
                    "error": str(e)
                }, 500

    @maintenance_ns.route('/detect-crashed')
    class DetectCrashedJobs(Resource):
        @maintenance_ns.param('timeoutMinutes', f'Timeout in minutes for crash detection (max {api_config["max_crash_detection_timeout"]})', type=int, default=api_config['crash_detection_timeout'])
        @maintenance_ns.marshal_with(models['api_response_model'])
        def post(self):
            """Detect and mark crashed jobs"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                timeout_minutes = request.args.get('timeoutMinutes', api_config['crash_detection_timeout'], type=int)
                
                if timeout_minutes < 1 or timeout_minutes > api_config['max_crash_detection_timeout']:
                    logger.warning(
                        "Invalid timeout for crash detection",
                        extra={'request_id': request_id, 'timeout_minutes': timeout_minutes}
                    )
                    return {
                        "success": False,
                        "message": f"Timeout minutes must be between 1 and {api_config['max_crash_detection_timeout']}",
                        "error": f"Timeout minutes must be between 1 and {api_config['max_crash_detection_timeout']}"
                    }, 400
                
                crashed_job_ids = extraction_service.detect_crashed_jobs(timeout_minutes)
                
                logger.info(
                    "Crash detection completed",
                    extra={
                        'request_id': request_id,
                        'crashed_count': len(crashed_job_ids),
                        'timeout_minutes': timeout_minutes
                    }
                )
                
                if len(crashed_job_ids) > 0:
                    log_security_event(
                        logger,
                        "crashed_jobs_detected",
                        severity='WARNING',
                        crashed_count=len(crashed_job_ids)
                    )
                
                return {
                    "success": True,
                    "data": {
                        "crashedJobIds": crashed_job_ids,
                        "crashedCount": len(crashed_job_ids),
                        "timeoutMinutes": timeout_minutes
                    },
                    "message": f"Detected {len(crashed_job_ids)} crashed jobs"
                }

            except Exception as e:
                logger.error(
                    "Error detecting crashed jobs",
                    extra={'request_id': request_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to detect crashed jobs: {str(e)}",
                    "error": str(e)
                }, 500
            
    @scan_ns.route('/<string:scan_id>/remove')
    class RemoveScan(Resource):
        @scan_ns.response(404, 'Scan not found')
        @scan_ns.response(400, 'Cannot remove active scan')
        @scan_ns.response(500, 'Internal server error')
        def delete(self, scan_id):
            """Remove a scan and its data"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                # Check if scan exists
                scan_status = extraction_service.get_scan_status(scan_id)
                if not scan_status:
                    logger.warning(
                        "Cannot remove scan: not found",
                        extra={'request_id': request_id, 'scan_id': scan_id}
                    )
                    return {
                        "success": False,
                        "message": f"No scan found with ID: {scan_id}",
                        "error": f"No scan found with ID: {scan_id}"
                    }, 404

                # Check if scan is still running
                if scan_status['status'] in ['running', 'pending']:
                    logger.warning(
                        "Cannot remove active scan",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_id,
                            'status': scan_status['status']
                        }
                    )
                    return {
                        "success": False,
                        "message": "Cannot remove active scan. Please cancel first.",
                        "error": "Cannot remove active scan"
                    }, 400

                result = extraction_service.remove_scan(scan_id)
                
                if result['success']:
                    logger.info(
                        "Scan removed",
                        extra={'request_id': request_id, 'scan_id': scan_id}
                    )
                    log_business_event(logger, "scan_removed", scan_id=scan_id)
                    return result
                else:
                    logger.error(
                        "Scan removal failed",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_id,
                            'reason': result.get('message')
                        }
                    )
                    return {
                        "success": False,
                        "message": result['message'],
                        "error": result['message']
                    }, 400

            except Exception as e:
                logger.error(
                    "Error removing scan",
                    extra={'request_id': request_id, 'scan_id': scan_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to remove scan: {str(e)}",
                    "error": str(e)
                }, 500

    @api.route('/stats')
    class ServiceStats(Resource):
        def get(self):
            """Get service statistics"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                stats = extraction_service.get_service_statistics()
                
                logger.debug(
                    "Service stats retrieved",
                    extra={
                        'request_id': request_id,
                        'total_scans': stats.get('total_scans', 0)
                    }
                )
                
                return {"success": True, "data": stats}

            except Exception as e:
                logger.error(
                    "Error getting service statistics",
                    extra={'request_id': request_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to retrieve service statistics: {str(e)}",
                    "error": str(e)
                }, 500

    @api.route('/health')
    class Health(Resource):
        def get(self):
            """Health check endpoint"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                pipeline_info = extraction_service.get_pipeline_info()
                
                logger.debug(
                    "Health check passed",
                    extra={'request_id': request_id, 'status': 'healthy'}
                )
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": config.DLT_PIPELINE_NAME,
                    "pipeline": pipeline_info
                }
                
            except Exception as e:
                logger.error(
                    "Health check failed",
                    extra={'request_id': request_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": config.DLT_PIPELINE_NAME,
                    "error": str(e)
                }, 500

    @scan_ns.route('/<string:scan_id>/pause')
    class PauseScan(Resource):
        @scan_ns.response(400, 'Cannot pause scan')
        @scan_ns.response(404, 'Scan not found')
        @scan_ns.response(500, 'Internal server error')
        def post(self, scan_id):
            """Pause a running scan"""
            request_id = getattr(g, 'request_id', str(uuid.uuid4()))
            
            try:
                result = extraction_service.pause_scan(scan_id)
                
                if result['success']:
                    logger.info(
                        "Scan paused successfully",
                        extra={'request_id': request_id, 'scan_id': scan_id}
                    )
                    return result
                else:
                    status_code = 404 if "not found" in result['message'].lower() else 400
                    logger.warning(
                        "Scan pause failed",
                        extra={
                            'request_id': request_id,
                            'scan_id': scan_id,
                            'reason': result.get('message')
                        }
                    )
                    return {
                        "success": False,
                        "message": result['message'],
                        "error": result['message']
                    }, status_code

            except Exception as e:
                logger.error(
                    "Error pausing scan",
                    extra={'request_id': request_id, 'scan_id': scan_id, 'error': str(e)},
                    exc_info=True
                )
                return {
                    "success": False,
                    "message": f"Failed to pause scan: {str(e)}",
                    "error": str(e)
                }, 500


    logger.info(
        "API created successfully",
        extra={
            'operation': 'api_creation',
            'service': config.DLT_PIPELINE_NAME
        }
    )

    return api