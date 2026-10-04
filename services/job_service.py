import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.sql import func

from models.models import Job, JobStatus, JobCheckpoint
from models.database import get_db_session_scope
from utils import deep_serialize, calculate_duration
from loki_logger import get_logger, log_business_event, log_security_event

from encrypter import Encrypter


class JobService:
    """Service for managing job lifecycle and operations"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.encrypter = Encrypter()

    def create_job(self, request_config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with get_db_session_scope() as db:
                job = Job.from_request_data(request_config)
                auth = request_config.get("auth")
                encrypted_auth = self.encrypter.encrypt(auth)
                job.config["auth"] = encrypted_auth

                job.status = JobStatus.PENDING.value
                db.add(job)
                db.flush()

                job_dict = job.to_dict()

                self.logger.info(
                    "Creating job",
                    extra={
                        "operation": "create_job",
                        "job_dict": job_dict,
                    },
                )

                self.logger.info(
                    "Job created",
                    extra={
                        "operation": "create_job",
                        "job_id": job.id,
                        "organization_id": job.organizationId,
                        "job_type": request_config.get("type"),
                    },
                )

                log_business_event(
                    self.logger,
                    "job_created",
                    job_id=job.id,
                    organization_id=job.organizationId,
                )

                return job_dict

        except Exception as e:
            self.logger.error(
                "Failed to create job",
                extra={
                    "operation": "create_job",
                    "error": str(e),
                    "organization_id": request_config.get("organizationId"),
                },
                exc_info=True,
            )
            raise

    def get_job(self, job_id: str, decrypt: bool = False) -> Optional[Dict[str, Any]]:
        try:
            with get_db_session_scope() as db:
                job = db.query(Job).filter(Job.id == job_id).first()

                if job:
                    self.logger.debug(
                        "Job retrieved",
                        extra={
                            "operation": "get_job",
                            "job_id": job_id,
                            "status": job.status,
                        },
                    )
                    job_dict = job.to_dict()

                    # Decrypt auth if requested and auth exists
                    if decrypt and job_dict.get("config").get("auth"):
                        try:
                            job_dict["config"]["auth"] = self.encrypter.decrypt(
                                job_dict["config"]["auth"]
                            )
                        except Exception as e:
                            self.logger.error(
                                "Failed to decrypt job auth",
                                extra={
                                    "operation": "get_job",
                                    "job_id": job_id,
                                    "error": str(e),
                                },
                            )
                            # Keep encrypted auth in case of decryption failure

                    return job_dict
                else:
                    self.logger.warning(
                        "Job not found",
                        extra={"operation": "get_job", "job_id": job_id},
                    )
                    return None
        except Exception as e:
            self.logger.error(
                "Error retrieving job",
                extra={"operation": "get_job", "job_id": job_id, "error": str(e)},
            )
            return None

        except Exception as e:
            self.logger.error(
                "Error retrieving job",
                extra={"operation": "get_job", "job_id": job_id, "error": str(e)},
                exc_info=True,
            )
            return None

    def update_job_status(
        self, job_id: str, status: JobStatus, **kwargs
    ) -> Optional[Dict[str, Any]]:
        try:
            with get_db_session_scope() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    old_status = job.status
                    job.status = status.value

                    for field, value in kwargs.items():
                        if field == "metadata":
                            setattr(job, "job_metadata", value)
                        elif hasattr(job, field):
                            setattr(job, field, value)

                    db.flush()

                    self.logger.info(
                        "Job status updated",
                        extra={
                            "operation": "update_job_status",
                            "job_id": job_id,
                            "old_status": old_status,
                            "new_status": status.value,
                        },
                    )

                    return deep_serialize(job.to_dict())

                self.logger.warning(
                    "Job not found for status update",
                    extra={"operation": "update_job_status", "job_id": job_id},
                )
                return None

        except Exception as e:
            self.logger.error(
                "Failed to update job status",
                extra={
                    "operation": "update_job_status",
                    "job_id": job_id,
                    "status": status.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return None

    def update_job_heartbeat(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            with get_db_session_scope() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.lastHeartbeat = func.now()
                    db.flush()

                    self.logger.debug(
                        "Job heartbeat updated",
                        extra={"operation": "update_heartbeat", "job_id": job_id},
                    )

                    return deep_serialize(job.to_dict())
                return None

        except Exception as e:
            self.logger.warning(
                "Failed to update heartbeat",
                extra={
                    "operation": "update_heartbeat",
                    "job_id": job_id,
                    "error": str(e),
                },
            )
            return None

    def complete_job(
        self, job_id: str, records_extracted: int, metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        result = self.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            endTime=func.now(),
            recordsExtracted=records_extracted,
            metadata=deep_serialize(metadata),
        )

        if result:
            self.logger.info(
                "Job completed",
                extra={
                    "operation": "complete_job",
                    "job_id": job_id,
                    "records_extracted": records_extracted,
                },
            )

            log_business_event(
                self.logger,
                "job_completed",
                job_id=job_id,
                records_extracted=records_extracted,
            )

        return result

    def fail_job(
        self, job_id: str, error_message: str, metadata: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        result = self.update_job_status(
            job_id,
            JobStatus.FAILED,
            endTime=func.now(),
            errorMessage=error_message,
            metadata=deep_serialize(metadata or {}),
        )

        if result:
            self.logger.error(
                "Job failed",
                extra={
                    "operation": "fail_job",
                    "job_id": job_id,
                    "error_message": error_message,
                },
            )

            log_business_event(
                self.logger, "job_failed", job_id=job_id, error_message=error_message
            )

        return result

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        try:
            with get_db_session_scope() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    self.logger.warning(
                        "Cannot cancel job: not found",
                        extra={"operation": "cancel_job", "job_id": job_id},
                    )
                    return {"success": False, "message": "Job not found"}

                if job.status in [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ]:
                    self.logger.warning(
                        "Cannot cancel job: invalid status",
                        extra={
                            "operation": "cancel_job",
                            "job_id": job_id,
                            "current_status": job.status,
                        },
                    )
                    return {
                        "success": False,
                        "message": f"Cannot cancel job with status: {job.status}",
                    }

                job.status = JobStatus.CANCELLED.value
                job.endTime = func.now()
                job.job_metadata = deep_serialize(
                    {"cancelled_at": datetime.now(timezone.utc).isoformat()}
                )
                db.flush()

                self.logger.info(
                    "Job cancelled", extra={"operation": "cancel_job", "job_id": job_id}
                )

                log_business_event(self.logger, "job_cancelled", job_id=job_id)

                return deep_serialize(
                    {
                        "success": True,
                        "scanId": job_id,
                        "status": job.status,
                        "message": "Job cancelled successfully",
                    }
                )

        except Exception as e:
            self.logger.error(
                "Error cancelling job",
                extra={"operation": "cancel_job", "job_id": job_id, "error": str(e)},
                exc_info=True,
            )
            return {"success": False, "message": f"Failed to cancel job: {str(e)}"}

    def pause_job(self, job_id: str) -> Dict[str, Any]:
        """Pause a job that is currently running or pending"""
        try:
            with get_db_session_scope() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    self.logger.warning(
                        "Cannot pause job: not found",
                        extra={"operation": "pause_job", "job_id": job_id},
                    )
                    return {"success": False, "message": "Job not found"}

                current_status = job.status

                # Define statuses that cannot be paused
                unpausable_statuses = [
                    JobStatus.COMPLETED.value,
                    JobStatus.CRASHED.value,
                    JobStatus.FAILED.value,
                    JobStatus.PAUSED.value,
                    JobStatus.CANCELLED.value,
                ]

                if current_status in unpausable_statuses:
                    self.logger.warning(
                        "Cannot pause job: invalid status",
                        extra={
                            "operation": "pause_job",
                            "job_id": job_id,
                            "current_status": current_status,
                        },
                    )
                    return {
                        "success": False,
                        "message": f"Cannot pause job with status: {current_status}. Only running or pending jobs can be paused.",
                    }

                # Only RUNNING and PENDING jobs can be paused
                if current_status not in [
                    JobStatus.RUNNING.value,
                    JobStatus.PENDING.value,
                ]:
                    self.logger.warning(
                        "Cannot pause job: unexpected status",
                        extra={
                            "operation": "pause_job",
                            "job_id": job_id,
                            "current_status": current_status,
                        },
                    )
                    return {
                        "success": False,
                        "message": f"Cannot pause job with status: {current_status}",
                    }

                # Update job status to paused
                job.status = JobStatus.PAUSED.value

                # Add pause metadata
                pause_metadata = {
                    "paused_at": datetime.now(timezone.utc).isoformat(),
                    "paused_from_status": current_status,
                    "pause_reason": "user_requested",
                }

                # Merge with existing metadata
                existing_metadata = job.job_metadata or {}
                if isinstance(existing_metadata, str):
                    import json

                    try:
                        existing_metadata = json.loads(existing_metadata)
                    except:
                        existing_metadata = {}

                existing_metadata.update(pause_metadata)
                job.job_metadata = deep_serialize(existing_metadata)

                db.flush()

                # Get latest checkpoint for progress information
                latest_checkpoint = self.get_latest_checkpoint(job_id)
                progress_info = {}
                if latest_checkpoint:
                    progress_info = {
                        "recordsProcessed": latest_checkpoint.get(
                            "recordsProcessed", 0
                        ),
                        "currentPage": latest_checkpoint.get("pageNumber", 0),
                        "phase": latest_checkpoint.get("phase", "unknown"),
                        "progressPercentage": latest_checkpoint.get(
                            "progress_percentage"
                        ),
                    }

                self.logger.info(
                    "Job paused successfully",
                    extra={
                        "operation": "pause_job",
                        "job_id": job_id,
                        "previous_status": current_status,
                        "records_processed": progress_info.get("recordsProcessed", 0),
                    },
                )

                log_business_event(
                    self.logger,
                    "job_paused",
                    job_id=job_id,
                    previous_status=current_status,
                    records_processed=progress_info.get("recordsProcessed", 0),
                )

                return deep_serialize(
                    {
                        "success": True,
                        "scanId": job_id,
                        "message": f"Job {job_id} has been paused successfully",
                        "data": {
                            "scanId": job_id,
                            "previousStatus": current_status,
                            "currentStatus": JobStatus.PAUSED.value,
                            "pausedAt": pause_metadata["paused_at"],
                            "progress": progress_info,
                        },
                    }
                )

        except Exception as e:
            self.logger.error(
                "Error pausing job",
                extra={"operation": "pause_job", "job_id": job_id, "error": str(e)},
                exc_info=True,
            )
            return {"success": False, "message": f"Failed to pause job: {str(e)}"}

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            with get_db_session_scope() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    return None

                result = job.to_dict()

                if result.get("endTime"):
                    duration = calculate_duration(
                        result["startTime"], result["endTime"]
                    )
                    if duration is not None:
                        result["duration"] = duration

                latest_checkpoint = self.get_latest_checkpoint(job_id)
                if latest_checkpoint:
                    result["checkpointInfo"] = {
                        "latestCheckpoint": latest_checkpoint,
                        "progress": latest_checkpoint.get("progress_percentage"),
                        "lastCheckpointAt": latest_checkpoint.get("createdAt"),
                    }

                self.logger.debug(
                    "Job status retrieved",
                    extra={
                        "operation": "get_job_status",
                        "job_id": job_id,
                        "status": result.get("status"),
                    },
                )

                return deep_serialize(result)

        except Exception as e:
            self.logger.error(
                "Error getting job status",
                extra={
                    "operation": "get_job_status",
                    "job_id": job_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return None

    def list_jobs(
        self, organization_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        try:
            with get_db_session_scope() as db:
                query = db.query(Job)
                if organization_id:
                    query = query.filter(Job.organizationId == organization_id)

                jobs = (
                    query.order_by(Job.startTime.desc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                result = []
                for job in jobs:
                    job_dict = job.to_dict()
                    if job_dict.get("endTime"):
                        duration = calculate_duration(
                            job_dict["startTime"], job_dict["endTime"]
                        )
                        if duration is not None:
                            job_dict["duration"] = duration
                    result.append(deep_serialize(job_dict))

                self.logger.debug(
                    "Jobs listed",
                    extra={
                        "operation": "list_jobs",
                        "count": len(result),
                        "organization_id": organization_id,
                        "limit": limit,
                        "offset": offset,
                    },
                )

                return result

        except Exception as e:
            self.logger.error(
                "Error listing jobs",
                extra={
                    "operation": "list_jobs",
                    "organization_id": organization_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return []

    def detect_crashed_jobs(self, timeout_minutes: int = 10) -> List[Dict[str, Any]]:
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                minutes=timeout_minutes
            )
            with get_db_session_scope() as db:
                crashed_jobs = (
                    db.query(Job)
                    .filter(
                        Job.status == JobStatus.RUNNING.value,
                        Job.lastHeartbeat < cutoff_time,
                    )
                    .all()
                )

                crashed_job_dicts = []
                for job in crashed_jobs:
                    job.status = JobStatus.CRASHED.value
                    crashed_job_dicts.append(deep_serialize(job.to_dict()))

                if crashed_job_dicts:
                    self.logger.warning(
                        "Crashed jobs detected",
                        extra={
                            "operation": "detect_crashed_jobs",
                            "crashed_count": len(crashed_job_dicts),
                            "timeout_minutes": timeout_minutes,
                        },
                    )

                    log_security_event(
                        self.logger,
                        "crashed_jobs_detected",
                        severity="WARNING",
                        crashed_count=len(crashed_job_dicts),
                        timeout_minutes=timeout_minutes,
                    )

                return crashed_job_dicts

        except Exception as e:
            self.logger.error(
                "Error detecting crashed jobs",
                extra={"operation": "detect_crashed_jobs", "error": str(e)},
                exc_info=True,
            )
            return []

    def save_checkpoint(
        self, job_id: str, checkpoint_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            with get_db_session_scope() as db:
                checkpoint = JobCheckpoint.create_checkpoint(job_id, **checkpoint_data)
                db.add(checkpoint)
                db.flush()

                self.logger.debug(
                    "Checkpoint saved",
                    extra={
                        "operation": "save_checkpoint",
                        "job_id": job_id,
                        "page_number": checkpoint_data.get("page_number", 0),
                    },
                )

                return deep_serialize(checkpoint.to_dict())

        except Exception as e:
            self.logger.error(
                "Failed to save checkpoint",
                extra={
                    "operation": "save_checkpoint",
                    "job_id": job_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def get_latest_checkpoint(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            with get_db_session_scope() as db:
                checkpoint = (
                    db.query(JobCheckpoint)
                    .filter(JobCheckpoint.job_id == job_id)
                    .order_by(JobCheckpoint.createdAt.desc())
                    .first()
                )
                return deep_serialize(checkpoint.to_dict()) if checkpoint else None

        except Exception as e:
            self.logger.error(
                "Failed to get latest checkpoint",
                extra={
                    "operation": "get_latest_checkpoint",
                    "job_id": job_id,
                    "error": str(e),
                },
            )
            return None

    def cleanup_old_jobs(self, days_old: int = 7) -> Dict[str, Any]:
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            with get_db_session_scope() as db:
                deleted_count = (
                    db.query(Job).filter(Job.startTime < cutoff_date).delete()
                )

            self.logger.info(
                "Old jobs cleaned up",
                extra={
                    "operation": "cleanup_old_jobs",
                    "deleted_count": deleted_count,
                    "days_old": days_old,
                },
            )

            log_security_event(
                self.logger,
                "jobs_cleanup_performed",
                deleted_count=deleted_count,
                days_old=days_old,
            )

            return {
                "deleted_jobs": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            self.logger.error(
                "Error during cleanup",
                extra={"operation": "cleanup_old_jobs", "error": str(e)},
                exc_info=True,
            )
            return {"deleted_jobs": 0, "error": str(e)}

    def get_job_statistics(
        self, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            with get_db_session_scope() as db:
                query = db.query(Job)
                if organization_id:
                    query = query.filter(Job.organizationId == organization_id)

                total_jobs = query.count()
                status_counts = {
                    status.value: query.filter(Job.status == status.value).count()
                    for status in JobStatus
                }

                week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                recent_jobs = query.filter(Job.startTime >= week_ago).count()

                total_records = db.query(func.sum(Job.recordsExtracted)).scalar() or 0

                self.logger.debug(
                    "Job statistics retrieved",
                    extra={
                        "operation": "get_job_statistics",
                        "total_jobs": total_jobs,
                        "organization_id": organization_id,
                    },
                )

                return deep_serialize(
                    {
                        "total_jobs": total_jobs,
                        "status_breakdown": status_counts,
                        "recent_jobs_7_days": recent_jobs,
                        "total_records_extracted": total_records,
                        "organization_filter": organization_id,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

        except Exception as e:
            self.logger.error(
                "Error getting job statistics",
                extra={"operation": "get_job_statistics", "error": str(e)},
                exc_info=True,
            )
            return {
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    def remove_job(self, job_id: str) -> bool:
        """Remove a job and all its checkpoints completely"""
        try:
            with get_db_session_scope() as db:
                # Remove checkpoints first
                deleted_checkpoints = (
                    db.query(JobCheckpoint)
                    .filter(JobCheckpoint.job_id == job_id)
                    .delete()
                )

                # Remove the job
                deleted_jobs = db.query(Job).filter(Job.id == job_id).delete()

                if deleted_jobs > 0:
                    db.commit()

                    self.logger.info(
                        "Job removed",
                        extra={
                            "operation": "remove_job",
                            "job_id": job_id,
                            "deleted_checkpoints": deleted_checkpoints,
                        },
                    )

                    log_business_event(self.logger, "job_removed", job_id=job_id)

                    return True
                else:
                    self.logger.warning(
                        "Job not found for removal",
                        extra={"operation": "remove_job", "job_id": job_id},
                    )
                    return False

        except Exception as e:
            self.logger.error(
                "Error removing job",
                extra={"operation": "remove_job", "job_id": job_id, "error": str(e)},
                exc_info=True,
            )
            return False

    def resume_job(self, job_id: str) -> Dict[str, Any]:
        """Resume a paused or crashed job"""
        try:
            with get_db_session_scope() as db:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    self.logger.warning(
                        "Cannot resume job: not found",
                        extra={"operation": "resume_job", "job_id": job_id},
                    )
                    return {"success": False, "message": "Job not found"}

                current_status = job.status

                # Define statuses that cannot be resumed
                non_resumable_statuses = [
                    JobStatus.COMPLETED.value,
                    JobStatus.CANCELLED.value,
                    JobStatus.FAILED.value,
                    JobStatus.RUNNING.value,
                    JobStatus.PENDING.value,
                    JobStatus.RESUMING.value,
                ]

                if current_status in non_resumable_statuses:
                    self.logger.warning(
                        "Cannot resume job: invalid status",
                        extra={
                            "operation": "resume_job",
                            "job_id": job_id,
                            "current_status": current_status,
                        },
                    )
                    return {
                        "success": False,
                        "message": f"Cannot resume job with status: {current_status}. Only paused or crashed jobs can be resumed.",
                    }

                # Only PAUSED and CRASHED jobs can be resumed
                if current_status not in [
                    JobStatus.PAUSED.value,
                    JobStatus.CRASHED.value,
                ]:
                    self.logger.warning(
                        "Cannot resume job: unexpected status",
                        extra={
                            "operation": "resume_job",
                            "job_id": job_id,
                            "current_status": current_status,
                        },
                    )
                    return {
                        "success": False,
                        "message": f"Cannot resume job with status: {current_status}",
                    }

                # Check if there's a checkpoint to resume from
                latest_checkpoint = self.get_latest_checkpoint(job_id)
                if not latest_checkpoint:
                    self.logger.warning(
                        "Cannot resume job: no checkpoint found",
                        extra={"operation": "resume_job", "job_id": job_id},
                    )
                    return {
                        "success": False,
                        "message": "No checkpoint found to resume from",
                    }

                # Update job status to resuming
                job.status = JobStatus.RESUMING.value
                job.lastHeartbeat = func.now()

                # Add resume metadata
                resume_metadata = {
                    "resumed_at": datetime.now(timezone.utc).isoformat(),
                    "resumed_from_status": current_status,
                    "resume_checkpoint": {
                        "page": latest_checkpoint.get("pageNumber", 0),
                        "records_processed": latest_checkpoint.get(
                            "recordsProcessed", 0
                        ),
                        "phase": latest_checkpoint.get("phase", "unknown"),
                    },
                }

                # Merge with existing metadata
                existing_metadata = job.job_metadata or {}
                if isinstance(existing_metadata, str):
                    import json

                    try:
                        existing_metadata = json.loads(existing_metadata)
                    except:
                        existing_metadata = {}

                existing_metadata.update(resume_metadata)
                job.job_metadata = deep_serialize(existing_metadata)

                db.flush()

                self.logger.info(
                    "Job resumed successfully",
                    extra={
                        "operation": "resume_job",
                        "job_id": job_id,
                        "previous_status": current_status,
                        "resume_page": latest_checkpoint.get("pageNumber", 0),
                        "records_processed": latest_checkpoint.get(
                            "recordsProcessed", 0
                        ),
                    },
                )

                log_business_event(
                    self.logger,
                    "job_resumed",
                    job_id=job_id,
                    previous_status=current_status,
                    resume_page=latest_checkpoint.get("pageNumber", 0),
                )

                return deep_serialize(
                    {
                        "success": True,
                        "scanId": job_id,
                        "message": f"Job {job_id} is resuming from checkpoint",
                        "data": {
                            "scanId": job_id,
                            "previousStatus": current_status,
                            "currentStatus": JobStatus.RESUMING.value,
                            "resumedAt": resume_metadata["resumed_at"],
                            "resumePoint": {
                                "page": latest_checkpoint.get("pageNumber", 0),
                                "recordsProcessed": latest_checkpoint.get(
                                    "recordsProcessed", 0
                                ),
                                "phase": latest_checkpoint.get("phase", "unknown"),
                                "cursor": latest_checkpoint.get("cursor"),
                            },
                        },
                    }
                )

        except Exception as e:
            self.logger.error(
                "Error resuming job",
                extra={"operation": "resume_job", "job_id": job_id, "error": str(e)},
                exc_info=True,
            )
            return {"success": False, "message": f"Failed to resume job: {str(e)}"}
