import hmac
import hashlib
from typing import Optional, Tuple
from flask import request, current_app, jsonify


def get_coordinator_key() -> str:
    """Retrieve coordinator secret key from application config or environment"""
    return current_app.config.get("COORDINATOR_KEY", "dev-coordinator-secret-key")


def verify_coordinator_auth() -> Tuple[bool, Optional[str]]:
    """
    Verify incoming request against Coordinator HMAC signature or Coordinator key.
    
    Returns:
        (is_authenticated, error_message)
    """
    coordinator_key = get_coordinator_key()
    if not coordinator_key:
        return False, "Coordinator key not configured on server"

    # 1. Check Direct Coordinator Key Header
    key_header = request.headers.get("X-Coordinator-Key")
    if key_header:
        if hmac.compare_digest(key_header, coordinator_key):
            return True, None

    # 2. Check HMAC Signature Header
    sig_header = request.headers.get("X-Coordinator-Signature")
    if sig_header:
        # Strip optional algorithm prefix e.g., 'sha256='
        raw_sig = sig_header[7:] if sig_header.lower().startswith("sha256=") else sig_header

        # Compute HMAC-SHA256 over raw request body payload
        payload = request.get_data()
        expected_sig = hmac.new(
            coordinator_key.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(raw_sig.lower(), expected_sig.lower()):
            return True, None

    return False, "Unauthorized: Invalid or missing coordinator signature"


def enforce_coordinator_auth():
    """
    Flask before_request hook to enforce coordinator authentication on protected endpoints.
    Whitelists public endpoints such as /, /health, /api/health, /docs, and OPTIONS requests.
    """
    # Allow CORS preflight requests
    if request.method == "OPTIONS":
        return None

    path = request.path

    # Whitelist public / unauthenticated endpoints
    whitelisted_exact = ["/", "/health", "/api/health", "/favicon.ico", "/swagger.json"]
    if path in whitelisted_exact:
        return None

    if path.startswith("/docs") or path.startswith("/swagger"):
        return None

    # Enforce coordinator authentication for all protected endpoints
    is_valid, err_msg = verify_coordinator_auth()
    if not is_valid:
        return jsonify({
            "success": False,
            "message": err_msg or "Unauthorized: Invalid or missing coordinator signature"
        }), 401
