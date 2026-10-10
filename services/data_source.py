import dlt
import logging
from typing import Dict, List, Any, Iterator, Optional, Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from config import Config
from loki_logger import get_logger, log_business_event
from .hubspot_api_service import HubSpotAPIService, mask_token, HubSpotAuthError, HubSpotAPIError


def parse_iso_datetime(val: Any) -> Optional[datetime]:
    """Parse ISO 8601 datetime string into a timezone-aware UTC datetime"""
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        try:
            # Replace Z with +00:00 for fromisoformat compatibility
            clean_str = val_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    return None


def transform_deal(record: Dict[str, Any], requested_properties: List[str], logger: logging.Logger) -> Dict[str, Any]:
    """
    Transform raw HubSpot deal record into a flattened dict matching database schema
    """
    deal_id = str(record.get("id", ""))
    props = record.get("properties", {}) or {}

    transformed: Dict[str, Any] = {
        "id": deal_id,
        "archived": bool(record.get("archived", False)),
        "created_at": parse_iso_datetime(record.get("createdAt")),
        "updated_at": parse_iso_datetime(record.get("updatedAt")),
    }

    # Numeric fields that require Decimal parsing
    numeric_fields = {"amount", "hs_acv", "hs_arr", "hs_closed_amount", "hs_forecast_amount", "hs_mrr", "hs_tcv"}
    # Date/Timestamp fields
    date_fields = {"closedate", "createdate", "hs_lastmodifieddate", "notes_last_contacted", "notes_last_updated", "notes_next_activity_date"}
    # Boolean fields
    bool_fields = {"hs_is_closed", "hs_is_closed_won"}

    for prop_name in requested_properties:
        raw_val = props.get(prop_name)

        # Empty string handling
        if raw_val == "":
            raw_val = None

        if raw_val is None:
            transformed[prop_name] = None
            continue

        if prop_name in numeric_fields:
            try:
                transformed[prop_name] = Decimal(str(raw_val))
            except (InvalidOperation, TypeError, ValueError):
                logger.warning(
                    f"Unparseable numeric property '{prop_name}' for deal ID {deal_id}: {raw_val}",
                    extra={"operation": "transform_deal", "deal_id": deal_id, "property": prop_name, "value": raw_val}
                )
                transformed[prop_name] = None
        elif prop_name in date_fields:
            transformed[prop_name] = parse_iso_datetime(raw_val)
        elif prop_name in bool_fields:
            if isinstance(raw_val, bool):
                transformed[prop_name] = raw_val
            elif isinstance(raw_val, str):
                transformed[prop_name] = raw_val.strip().lower() in ("true", "1", "yes")
            else:
                transformed[prop_name] = bool(raw_val)
        else:
            transformed[prop_name] = str(raw_val).strip()

    return transformed


def create_data_source(
    job_config: Dict[str, Any],
    auth_config: Dict[str, Any],
    filters: Dict[str, Any],
    checkpoint_callback: Optional[Callable] = None,
    check_cancel_callback: Optional[Callable] = None,
    check_pause_callback: Optional[Callable] = None,
    resume_from: Optional[Dict[str, Any]] = None,
):
    """
    Create DLT source function for HubSpot Deals data extraction with checkpoint support
    """
    logger = get_logger(__name__)

    access_token = auth_config.get("accessToken")
    if not access_token:
        raise ValueError("No access token found in auth configuration")

    organization_id = job_config.get("organizationId") or filters.get("organization_id")
    if not organization_id:
        raise ValueError("No organization ID found in job configuration")

    # Initialize HubSpot API Service
    api_service = HubSpotAPIService(
        base_url=Config.HUBSPOT_API_BASE_URL,
        timeout=Config.HUBSPOT_API_TIMEOUT,
        rate_limit=Config.HUBSPOT_API_RATE_LIMIT,
        window_seconds=Config.HUBSPOT_RATE_LIMIT_WINDOW_SECONDS,
        max_retries=Config.HUBSPOT_API_MAX_RETRIES,
        backoff_seconds=Config.HUBSPOT_API_RETRY_BACKOFF_SECONDS,
        test_delay_seconds=Config.HUBSPOT_TEST_DELAY_SECONDS,
    )

    # Validate token up front
    val_res = api_service.validate_credentials(access_token)
    if not val_res.get("valid"):
        err_msg = val_res.get("error") or f"Invalid credentials (status code {val_res.get('status_code')})"
        logger.error(
            "HubSpot credentials validation failed",
            extra={"organization_id": organization_id, "token": mask_token(access_token), "error": err_msg}
        )
        raise HubSpotAuthError(f"HubSpot credentials validation failed: {err_msg}")

    # Properties list to request
    default_properties = [
        "dealname", "amount", "dealstage", "pipeline", "closedate",
        "createdate", "hs_lastmodifieddate", "description", "dealtype",
        "hubspot_owner_id", "hs_priority", "hs_is_closed", "hs_is_closed_won"
    ]
    requested_properties = filters.get("properties") or default_properties

    logger.info(
        "Starting HubSpot Deals data extraction",
        extra={
            "organization_id": organization_id,
            "scan_id": filters.get("scan_id", "unknown"),
            "token": mask_token(access_token),
            "properties_count": len(requested_properties),
        },
    )

    @dlt.resource(
        name="hubspot_deals",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "dealname": {"data_type": "text"},
            "amount": {"data_type": "decimal"},
            "dealstage": {"data_type": "text"},
            "pipeline": {"data_type": "text"},
            "closedate": {"data_type": "timestamp"},
            "createdate": {"data_type": "timestamp"},
            "hs_lastmodifieddate": {"data_type": "timestamp"},
            "description": {"data_type": "text"},
            "dealtype": {"data_type": "text"},
            "hubspot_owner_id": {"data_type": "text"},
            "hs_priority": {"data_type": "text"},
            "hs_is_closed": {"data_type": "bool"},
            "hs_is_closed_won": {"data_type": "bool"},
            "created_at": {"data_type": "timestamp"},
            "updated_at": {"data_type": "timestamp"},
            "archived": {"data_type": "bool"},
            "_extracted_at": {"data_type": "timestamp"},
            "_scan_id": {"data_type": "text"},
            "_tenant_id": {"data_type": "text"},
            "_page_number": {"data_type": "bigint"},
            "_source_service": {"data_type": "text"},
        },
    )
    def get_deals_resource() -> Iterator[Dict[str, Any]]:
        """Extract deals from HubSpot API and yield transformed records with checkpointing"""

        if resume_from:
            after = resume_from.get("cursor")
            page_count = resume_from.get("page_number", 0)
            total_records = resume_from.get("records_processed", 0)
            logger.info(
                "Resuming data extraction",
                extra={
                    "operation": "data_extraction",
                    "page_number": page_count + 1,
                    "total_processed": total_records,
                    "cursor": after,
                },
            )
        else:
            after = None
            page_count = 0
            total_records = 0
            logger.info(
                "Starting fresh data extraction",
                extra={"operation": "data_extraction", "source": "hubspot_deals"},
            )

        checkpoint_interval = Config.CHECKPOINT_EVERY_N_PAGES
        job_id = filters.get("scan_id", "unknown")
        max_pages = Config.MAX_PAGES
        page_size = Config.HUBSPOT_PAGE_SIZE
        include_archived = bool(filters.get("includeArchived", False))

        while page_count < max_pages:
            # Check for cancellation
            if check_cancel_callback and check_cancel_callback(job_id):
                logger.info("Extraction cancelled by user", extra={"job_id": job_id, "page_number": page_count + 1})
                if checkpoint_callback:
                    try:
                        checkpoint_callback(job_id, {
                            "phase": "main_data_cancelled",
                            "records_processed": total_records,
                            "cursor": after,
                            "page_number": page_count,
                            "batch_size": page_size,
                            "checkpoint_data": {"cancellation_reason": "user_requested", "service": "hubspot_deals"}
                        })
                    except Exception as e:
                        logger.warning("Failed to save cancellation checkpoint", extra={"job_id": job_id, "error": str(e)})
                break

            # Check for pause
            if check_pause_callback and check_pause_callback(job_id):
                logger.info("Extraction paused by user", extra={"job_id": job_id, "page_number": page_count + 1})
                if checkpoint_callback:
                    try:
                        checkpoint_callback(job_id, {
                            "phase": "main_data_paused",
                            "records_processed": total_records,
                            "cursor": after,
                            "page_number": page_count,
                            "batch_size": page_size,
                            "checkpoint_data": {"pause_reason": "user_requested", "service": "hubspot_deals"}
                        })
                    except Exception as e:
                        logger.warning("Failed to save pause checkpoint", extra={"job_id": job_id, "error": str(e)})
                break

            logger.debug("Fetching deals page", extra={"job_id": job_id, "page_number": page_count + 1, "cursor": after})

            try:
                data = api_service.get_deals(
                    access_token=access_token,
                    limit=page_size,
                    after=after,
                    properties=requested_properties,
                    archived=include_archived
                )
            except Exception as fetch_err:
                logger.error("Error fetching deals page", extra={"job_id": job_id, "page_number": page_count + 1, "error": str(fetch_err)})
                if checkpoint_callback:
                    try:
                        checkpoint_callback(job_id, {
                            "phase": "main_data_error",
                            "records_processed": total_records,
                            "cursor": after,
                            "page_number": page_count,
                            "checkpoint_data": {"error": str(fetch_err), "service": "hubspot_deals"}
                        })
                    except Exception:
                        pass
                raise fetch_err

            results = data.get("results", [])
            page_records = 0
            extracted_at_iso = datetime.now(timezone.utc).isoformat()

            for record in results:
                # Check pause mid-page
                if check_pause_callback and check_pause_callback(job_id):
                    logger.info("Extraction paused mid-page", extra={"job_id": job_id, "page_number": page_count + 1})
                    if checkpoint_callback:
                        try:
                            checkpoint_callback(job_id, {
                                "phase": "main_data_paused_mid_page",
                                "records_processed": total_records + page_records,
                                "cursor": after,
                                "page_number": page_count,
                                "checkpoint_data": {"pause_reason": "user_requested_mid_page", "service": "hubspot_deals"}
                            })
                        except Exception as e:
                            logger.warning("Failed to save mid-page pause checkpoint", extra={"job_id": job_id, "error": str(e)})
                    return

                transformed = transform_deal(record, requested_properties, logger)
                transformed.update({
                    "_extracted_at": extracted_at_iso,
                    "_scan_id": job_id,
                    "_tenant_id": organization_id,
                    "_page_number": page_count + 1,
                    "_source_service": "hubspot_deals"
                })

                yield transformed
                page_records += 1

            total_records += page_records
            page_count += 1

            # Determine next cursor
            paging = data.get("paging")
            next_cursor = None
            if paging and paging.get("next") and paging["next"].get("after"):
                next_cursor = paging["next"]["after"]

            current_state = filters.get("_extraction_state", {})
            last_cursor = current_state.get("cursor") if current_state else None

            # Update in-memory extraction state (tracking fetched state before DLT load completes)
            filters["_extraction_state"] = {
                "cursor": next_cursor if next_cursor is not None else last_cursor,
                "records_processed": total_records,
                "page_number": page_count,
                "last_page_records": page_records
            }

            if not next_cursor:
                logger.info("Data extraction completed", extra={"job_id": job_id, "total_records": total_records, "total_pages": page_count})
                break

            after = next_cursor

    return [get_deals_resource]