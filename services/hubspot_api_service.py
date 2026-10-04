import time
import random
import threading
import requests
from typing import Dict, List, Any, Optional, Iterator
from config import Config
from loki_logger import get_logger

logger = get_logger(__name__)


def mask_token(access_token: str) -> str:
    """Mask sensitive HubSpot access token for logging (never reveals any part of the real token)"""
    if not access_token:
        return "<empty>"
    return "pat-****"


class HubSpotAPIError(Exception):
    """Base exception for HubSpot API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.retryable = retryable


class HubSpotAuthError(HubSpotAPIError):
    """Exception raised for 401 Unauthorized / 403 Forbidden errors (non-retryable)"""
    def __init__(self, message: str, status_code: int = 401, error_code: Optional[str] = None):
        super().__init__(message=message, status_code=status_code, error_code=error_code, retryable=False)


class HubSpotRateLimitError(HubSpotAPIError):
    """Exception raised when rate limit retries are exhausted (429)"""
    def __init__(self, message: str, status_code: int = 429, error_code: Optional[str] = None):
        super().__init__(message=message, status_code=status_code, error_code=error_code, retryable=True)


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter"""
    def __init__(self, max_requests: int = 150, window_seconds: float = 10.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps: List[float] = []
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.time()
            # Drop timestamps outside the current window
            self.timestamps = [t for t in self.timestamps if now - t < self.window_seconds]
            if len(self.timestamps) >= self.max_requests:
                sleep_time = self.window_seconds - (now - self.timestamps[0])
                if sleep_time > 0:
                    logger.warning(
                        "Sliding window rate limit reached, sleeping",
                        extra={"operation": "rate_limit", "sleep_seconds": round(sleep_time, 2)}
                    )
                    time.sleep(sleep_time)
                now = time.time()
                self.timestamps = [t for t in self.timestamps if now - t < self.window_seconds]
            self.timestamps.append(time.time())


class HubSpotAPIService:
    """Service client for HubSpot CRM API v3 (Deals)"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        rate_limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        backoff_seconds: Optional[float] = None,
        test_delay_seconds: Optional[float] = None,
    ):
        self.base_url = (base_url or Config.HUBSPOT_API_BASE_URL).rstrip('/')
        self.timeout = timeout if timeout is not None else Config.HUBSPOT_API_TIMEOUT
        self.rate_limit = rate_limit if rate_limit is not None else Config.HUBSPOT_API_RATE_LIMIT
        self.window_seconds = window_seconds if window_seconds is not None else Config.HUBSPOT_RATE_LIMIT_WINDOW_SECONDS
        self.max_retries = max_retries if max_retries is not None else Config.HUBSPOT_API_MAX_RETRIES
        self.backoff_seconds = backoff_seconds if backoff_seconds is not None else Config.HUBSPOT_API_RETRY_BACKOFF_SECONDS
        self.test_delay_seconds = test_delay_seconds if test_delay_seconds is not None else Config.HUBSPOT_TEST_DELAY_SECONDS

        self.limiter = SlidingWindowRateLimiter(max_requests=self.rate_limit, window_seconds=self.window_seconds)
        self.session = requests.Session()

    def _make_request(self, method: str, endpoint: str, access_token: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an HTTP request with rate limiting, retries, and error handling"""
        if not access_token:
            raise HubSpotAuthError("Missing access token", status_code=401)

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.test_delay_seconds > 0:
            time.sleep(self.test_delay_seconds)

        attempt = 0
        masked_tok = mask_token(access_token)

        while True:
            attempt += 1
            self.limiter.acquire()
            start_time = time.time()

            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )
                duration_ms = round((time.time() - start_time) * 1000, 2)

                if response.status_code == 200:
                    data = response.json()
                    record_count = len(data.get("results", [])) if isinstance(data, dict) else (len(data) if isinstance(data, list) else 0)
                    logger.debug(
                        "HubSpot API request successful",
                        extra={
                            "operation": "hubspot_api_request",
                            "endpoint": endpoint,
                            "status_code": 200,
                            "duration_ms": duration_ms,
                            "record_count": record_count,
                            "token": masked_tok
                        }
                    )
                    return data

                # Auth Errors: 401, 403 (No retries)
                if response.status_code in (401, 403):
                    err_msg = f"Authentication error {response.status_code} for endpoint {endpoint}"
                    try:
                        err_body = response.json()
                        err_msg += f": {err_body.get('message', response.text)}"
                    except Exception:
                        pass
                    raise HubSpotAuthError(err_msg, status_code=response.status_code)

                # Rate limit: 429
                if response.status_code == 429:
                    retry_after_hdr = response.headers.get("Retry-After")
                    try:
                        retry_after = float(retry_after_hdr) if retry_after_hdr else 10.0
                    except ValueError:
                        retry_after = 10.0

                    if attempt <= self.max_retries:
                        logger.warning(
                            "HubSpot API rate limit 429 encountered, waiting to retry",
                            extra={
                                "operation": "hubspot_api_rate_limit",
                                "attempt": attempt,
                                "max_retries": self.max_retries,
                                "retry_after": retry_after
                            }
                        )
                        time.sleep(retry_after)
                        continue
                    else:
                        raise HubSpotRateLimitError(f"Rate limit 429 exceeded after {attempt} attempts", status_code=429)

                # 4xx client errors (non-retryable except 429 handled above)
                if 400 <= response.status_code < 500:
                    err_msg = f"HubSpot API error {response.status_code}"
                    corr_id = None
                    try:
                        err_body = response.json()
                        err_msg = err_body.get("message", err_msg)
                        corr_id = err_body.get("correlationId")
                    except Exception:
                        pass
                    if corr_id:
                        err_msg += f" (correlationId: {corr_id})"
                    raise HubSpotAPIError(err_msg, status_code=response.status_code, error_code="CLIENT_ERROR", retryable=False)

                # 5xx server errors
                if response.status_code >= 500:
                    if attempt <= self.max_retries:
                        backoff = self.backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                        logger.warning(
                            "HubSpot API server error, retrying",
                            extra={
                                "operation": "hubspot_api_retry",
                                "status_code": response.status_code,
                                "attempt": attempt,
                                "backoff_seconds": round(backoff, 2)
                            }
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        raise HubSpotAPIError(
                            f"HubSpot API server error {response.status_code} after {attempt} attempts",
                            status_code=response.status_code,
                            retryable=True
                        )

            except (requests.Timeout, requests.ConnectionError) as e:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                if attempt <= self.max_retries:
                    backoff = self.backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    logger.warning(
                        "HubSpot API network error, retrying",
                        extra={
                            "operation": "hubspot_api_retry",
                            "error": str(e),
                            "attempt": attempt,
                            "backoff_seconds": round(backoff, 2)
                        }
                    )
                    time.sleep(backoff)
                    continue
                else:
                    raise HubSpotAPIError(f"HubSpot API network request failed: {str(e)}", status_code=504, retryable=True)

    def validate_credentials(self, access_token: str) -> Dict[str, Any]:
        """Validate access token with a quick GET request (limit=1)"""
        try:
            self._make_request("GET", "/crm/v3/objects/deals", access_token, params={"limit": 1})
            return {"valid": True, "status_code": 200, "error": None}
        except HubSpotAuthError as e:
            return {"valid": False, "status_code": e.status_code, "error": e.message}
        except Exception as e:
            return {"valid": False, "status_code": getattr(e, "status_code", 500), "error": str(e)}

    def get_deals(
        self,
        access_token: str,
        limit: int = 100,
        after: Optional[str] = None,
        properties: Optional[List[str]] = None,
        archived: bool = False
    ) -> Dict[str, Any]:
        """Fetch one page of deals from HubSpot CRM API v3"""
        clamped_limit = max(1, min(100, limit))
        params: Dict[str, Any] = {"limit": clamped_limit, "archived": str(archived).lower()}
        if after:
            params["after"] = after
        if properties:
            params["properties"] = ",".join(properties)

        return self._make_request("GET", "/crm/v3/objects/deals", access_token, params=params)

    def get_deal_properties(self, access_token: str) -> List[Dict[str, Any]]:
        """Get definitions of deal properties from HubSpot"""
        data = self._make_request("GET", "/crm/v3/properties/deals", access_token)
        return data.get("results", [])

    def iter_deals(
        self,
        access_token: str,
        limit: int = 100,
        properties: Optional[List[str]] = None,
        archived: bool = False
    ) -> Iterator[Dict[str, Any]]:
        """Generator that yields page responses for deals until no more pages exist"""
        after = None
        while True:
            page = self.get_deals(access_token, limit=limit, after=after, properties=properties, archived=archived)
            yield page
            paging = page.get("paging")
            if paging and paging.get("next") and paging["next"].get("after"):
                after = paging["next"]["after"]
            else:
                break
