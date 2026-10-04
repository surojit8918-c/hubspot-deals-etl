import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import time
import json
from loki_logger import get_logger, log_api_call


class APIService:
    """
    Service for interacting with Hubspot_Deals APIs
    """
    
    def __init__(self, base_url: str = "https://api.hubspot_deals.com", test_delay_seconds: float = 0):
        self.base_url = base_url.rstrip('/')
        self.test_delay_seconds = test_delay_seconds  # Add configurable delay for testing
        self.logger = get_logger(__name__)
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Hubspot_Deals-Data-Extraction-Service/1.0'
        })
        
        self.logger.debug(
            "API service initialized",
            extra={
                'operation': 'api_service_init', 
                'base_url': base_url,
                'test_delay_seconds': test_delay_seconds
            }
        )
    
    def set_access_token(self, token: str):
        """Set the Hubspot_Deals API access token"""
        self.session.headers.update({
            'Authorization': f'Bearer {token}'
        })
        self.logger.debug("Access token set", extra={'operation': 'token_set'})
    
    def get_data(self, 
                 access_token: str,
                 limit: int = 100, 
                 after: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """
        Get data from Hubspot_Deals API with optional test delay
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(
                "Starting data retrieval",
                extra={
                    'operation': 'get_data',
                    'limit': limit,
                    'has_cursor': after is not None,
                    'test_delay_seconds': self.test_delay_seconds
                }
            )
            
            # Add test delay to simulate slow API calls for cancel/pause testing
            if self.test_delay_seconds > 0:
                self.logger.info(
                    f"Test delay: sleeping for {self.test_delay_seconds} seconds",
                    extra={'operation': 'get_data', 'delay_type': 'test_delay'}
                )
                time.sleep(self.test_delay_seconds)
            
            # Set authentication headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Build parameters
            params = {
                'limit': min(limit, 100),  # API limit
            }
            
            if after:
                params['after'] = after
            
            # Add additional parameters (excluding test-specific ones)
            for key, value in kwargs.items():
                if not key.startswith('_test_') and key not in ['scan_id']:
                    params[key] = value
            
            # TODO: Replace with appropriate Hubspot_Deals API endpoint
            url = f"{self.base_url}/v1/data"
            
            response = self.session.get(url, params=params, headers=headers)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                self.logger.warning(
                    "Rate limited, retrying",
                    extra={
                        'operation': 'get_data',
                        'retry_after': retry_after,
                        'status_code': 429
                    }
                )
                time.sleep(retry_after)
                response = self.session.get(url, params=params, headers=headers)
            
            response.raise_for_status()
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            result = response.json()
            
            self.logger.info(
                "Data retrieved successfully",
                extra={
                    'operation': 'get_data',
                    'status_code': response.status_code,
                    'duration_ms': round(duration_ms, 2),
                    'result_count': len(result.get('results', [])),
                    'has_more': result.get('paging', {}).get('next') is not None
                }
            )
            
            log_api_call(
                self.logger,
                "hubspot_deals_get_data",
                method='GET',
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2)
            )
            
            return result
            
        except requests.exceptions.RequestException as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.logger.error(
                "Error fetching data",
                extra={
                    'operation': 'get_data',
                    'error': str(e),
                    'duration_ms': round(duration_ms, 2),
                    'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                },
                exc_info=True
            )
            
            log_api_call(
                self.logger,
                "hubspot_deals_get_data",
                method='GET',
                status_code=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else 500,
                duration_ms=round(duration_ms, 2)
            )
            
            raise

    def validate_token(self, access_token: str) -> bool:
        """
        Validate Hubspot_Deals API access token
        """
        try:
            self.logger.debug(
                "Validating access token",
                extra={'operation': 'validate_token'}
            )
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # TODO: Replace with appropriate Hubspot_Deals validation endpoint
            url = f"{self.base_url}/v1/me"
            params = {'limit': 1}
            
            response = self.session.get(url, params=params, headers=headers)
            is_valid = response.status_code == 200
            
            if is_valid:
                self.logger.info(
                    "Token validation successful",
                    extra={'operation': 'validate_token'}
                )
            else:
                self.logger.warning(
                    "Token validation failed",
                    extra={
                        'operation': 'validate_token',
                        'status_code': response.status_code
                    }
                )
            
            return is_valid
            
        except requests.exceptions.RequestException as e:
            self.logger.error(
                "Token validation error",
                extra={'operation': 'validate_token', 'error': str(e)},
                exc_info=True
            )
            return False
    
    def get_api_usage(self, auth_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get API usage information from Hubspot_Deals headers
        """
        try:
            access_token = auth_config.get('accessToken')
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # TODO: Replace with appropriate Hubspot_Deals endpoint
            url = f"{self.base_url}/v1/me"
            params = {'limit': 1}
            
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                # TODO: Update based on Hubspot_Deals rate limit headers
                usage_info = {
                    'daily_limit': response.headers.get('X-RateLimit-Daily'),
                    'daily_remaining': response.headers.get('X-RateLimit-Daily-Remaining'),
                    'interval_limit': response.headers.get('X-RateLimit-Interval'),
                    'interval_remaining': response.headers.get('X-RateLimit-Remaining'),
                    'reset_timestamp': response.headers.get('X-RateLimit-Reset'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                filtered_usage = {k: v for k, v in usage_info.items() if v is not None}
                
                if filtered_usage:
                    self.logger.debug(
                        "API usage info retrieved",
                        extra={
                            'operation': 'get_api_usage',
                            'daily_remaining': filtered_usage.get('daily_remaining'),
                            'interval_remaining': filtered_usage.get('interval_remaining')
                        }
                    )
                
                return filtered_usage if filtered_usage else None
            
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(
                "Could not retrieve API usage",
                extra={'operation': 'get_api_usage', 'error': str(e)}
            )
            return None
    
    def get_account_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get Hubspot_Deals account information
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # TODO: Replace with appropriate Hubspot_Deals account endpoint
            url = f"{self.base_url}/v1/account"
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                account_info = response.json()
                self.logger.debug(
                    "Account info retrieved",
                    extra={
                        'operation': 'get_account_info',
                        'account_id': account_info.get('id'),
                        'account_name': account_info.get('name')
                    }
                )
                return account_info
            
            return None
            
        except requests.exceptions.RequestException as e:
            self.logger.debug(
                "Account info not available",
                extra={'operation': 'get_account_info', 'error': str(e)}
            )
            return None

    def test_connection(self, access_token: str) -> Dict[str, Any]:
        """
        Test connection to Hubspot_Deals API
        """
        self.logger.info(
            "Testing API connection",
            extra={'operation': 'test_connection'}
        )
        
        results = {
            'token_valid': False,
            'api_reachable': False,
            'data_accessible': False,
            'account_info': None,
            'usage_info': None,
            'error': None
        }
        
        try:
            # Test token validation
            results['token_valid'] = self.validate_token(access_token)
            results['api_reachable'] = results['token_valid']
            
            if results['token_valid']:
                # Get additional info
                results['account_info'] = self.get_account_info(access_token)
                results['usage_info'] = self.get_api_usage({'accessToken': access_token})
                
                # Test basic data access
                try:
                    test_data = self.get_data(access_token, limit=1)
                    results['data_accessible'] = True
                    
                    self.logger.info(
                        "Connection test successful",
                        extra={
                            'operation': 'test_connection',
                            'token_valid': results['token_valid'],
                            'data_accessible': results['data_accessible']
                        }
                    )
                    
                except Exception as e:
                    self.logger.warning(
                        "Data access test failed",
                        extra={'operation': 'test_connection', 'error': str(e)}
                    )
            else:
                self.logger.warning(
                    "Connection test failed - invalid token",
                    extra={'operation': 'test_connection'}
                )
                
        except Exception as e:
            results['error'] = str(e)
            self.logger.error(
                "Connection test error",
                extra={'operation': 'test_connection', 'error': str(e)},
                exc_info=True
            )
        
        return results