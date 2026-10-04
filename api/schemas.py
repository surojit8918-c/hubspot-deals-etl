"""
Marshmallow schemas for HubSpot User Extraction API
Input validation and serialization using Marshmallow
"""
from marshmallow import Schema, fields, validate, ValidationError, post_load
from datetime import datetime
import re

class AuthSchema(Schema):
    """Authentication schema"""
    accessToken = fields.Str(
        required=True,
        validate=validate.Length(min=10),
        error_messages={'required': 'Access token is required'}
    )

    teneantUrl = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Regexp(
            r'^(https?://)?[a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})+(/.*)?$',
            error='Invalid URL format'
        )
    )
    
    @post_load
    def validate_token_format(self, data, **kwargs):
        """Additional validation for token format"""
        token = data.get('accessToken')
        if token and len(token) < 10:
            raise ValidationError('Access token must be at least 10 characters long')
        return data

class DateRangeSchema(Schema):
    """Date range schema"""
    startDate = fields.Str(
        validate=validate.Regexp(
            r'^\d{4}-\d{2}-\d{2}$',
            error='Date must be in YYYY-MM-DD format'
        ),
        allow_none=True
    )
    endDate = fields.Str(
        validate=validate.Regexp(
            r'^\d{4}-\d{2}-\d{2}$',
            error='Date must be in YYYY-MM-DD format'
        ),
        allow_none=True
    )
    
    @post_load
    def validate_date_range(self, data, **kwargs):
        """Validate that start date is before end date"""
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    raise ValidationError('Start date must be before end date')
            except ValueError:
                raise ValidationError('Invalid date format')
        
        return data

class FiltersSchema(Schema):
    """Filters schema"""
    properties = fields.List(
        fields.Str(),
        allow_none=True,
        validate=validate.Length(min=1),
        error_messages={'validator_failed': 'Properties list cannot be empty'}
    )
    includeArchived = fields.Bool(
        missing=False,
        default=False
    )
    dateRange = fields.Nested(DateRangeSchema, allow_none=True)

class ScanConfigSchema(Schema):
    """Scan configuration schema"""
    scanId = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=255),
            validate.Regexp(
                r'^[a-zA-Z0-9_-]+$',
                error='Scan ID can only contain letters, numbers, underscores, and hyphens'
            )
        ],
        error_messages={'required': 'Scan ID is required'}
    )
    organizationId = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        error_messages={'required': 'Organization ID is required'}
    )
    type = fields.List(
        fields.Str(validate=validate.OneOf(['user'])),
        required=True,
        validate=validate.Length(min=1),
        error_messages={
            'required': 'Type is required',
            'validator_failed': 'Type must contain at least one value and only "user" is supported'
        }
    )
    auth = fields.Nested(
        AuthSchema,
        required=True,
        error_messages={'required': 'Authentication is required'}
    )
    filters = fields.Nested(FiltersSchema, missing=dict, default=dict)

class ScanRequestSchema(Schema):
    """Complete scan request schema"""
    config = fields.Nested(
        ScanConfigSchema,
        required=True,
        error_messages={'required': 'Config is required'}
    )

class PaginationSchema(Schema):
    """Pagination parameters schema"""
    limit = fields.Int(
        validate=validate.Range(min=1, max=1000),
        missing=100,
        default=100,
        error_messages={'validator_failed': 'Limit must be between 1 and 1000'}
    )
    offset = fields.Int(
        validate=validate.Range(min=0),
        missing=0,
        default=0,
        error_messages={'validator_failed': 'Offset cannot be negative'}
    )

class CleanupRequestSchema(Schema):
    """Cleanup request schema"""
    daysOld = fields.Int(
        validate=validate.Range(min=1, max=365),
        missing=7,
        default=7,
        error_messages={
            'validator_failed': 'daysOld must be between 1 and 365 days'
        }
    )

class ScanConfig:
    """Scan configuration data class"""
    def __init__(self, scanId: str, organizationId: str, type: list, auth: dict, filters: dict = None):
        self.scanId = scanId
        self.organizationId = organizationId
        self.type = type
        self.auth = auth
        self.filters = filters or {}

# Schema instances for reuse
scan_config_schema = ScanConfigSchema()
scan_request_schema = ScanRequestSchema()
pagination_schema = PaginationSchema()
cleanup_request_schema = CleanupRequestSchema()

def validate_scan_request(json_data: dict) -> dict:
    """Validate scan request data and return validated config"""
    try:
        validated = scan_request_schema.load(json_data)
        return validated['config']
    except ValidationError as err:
        raise err

def validate_pagination_params(limit, offset, max_limit: int = 1000) -> tuple:
    """Validate pagination parameters"""
    try:
        data = {'limit': limit, 'offset': offset}
        # Create a temporary schema with custom max limit
        temp_schema = PaginationSchema()
        temp_schema.fields['limit'].validate = validate.Range(min=1, max=max_limit)
        validated = temp_schema.load(data)
        return validated['limit'], validated['offset']
    except ValidationError as err:
        raise err

def validate_cleanup_request(json_data: dict) -> int:
    """Validate cleanup request and return days_old"""
    try:
        validated = cleanup_request_schema.load(json_data)
        return validated['daysOld']
    except ValidationError as err:
        raise err