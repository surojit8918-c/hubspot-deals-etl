from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    Boolean,
    JSON,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, List, Optional, Any
from enum import Enum
import json

Base = declarative_base()

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CRASHED = "crashed"
    RESUMING = "resuming"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(255), primary_key=True)  # This is the scanId
    organizationId = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False, default="user")  # job type
    status = Column(String(50), nullable=False, default=JobStatus.PENDING.value)
    startTime = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    endTime = Column(DateTime(timezone=True), nullable=True)
    lastHeartbeat = Column(
        DateTime(timezone=True), nullable=True
    )  # For crash detection
    recordsExtracted = Column(Integer, default=0)
    errorMessage = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)  # Store complete job configuration
    job_metadata = Column(
        JSON, nullable=True
    )  # Renamed from 'metadata' to avoid conflict

    # Relationship to checkpoints
    checkpoints = relationship(
        "JobCheckpoint", back_populates="job", cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "scanId": self.id,  # Keep API compatibility
            "organizationId": self.organizationId,
            "type": self.type,
            "status": self.status,
            "startTime": self.startTime.isoformat() if self.startTime else None,
            "endTime": self.endTime.isoformat() if self.endTime else None,
            "lastHeartbeat": (
                self.lastHeartbeat.isoformat() if self.lastHeartbeat else None
            ),
            "recordsExtracted": self.recordsExtracted,
            "errorMessage": self.errorMessage,
            "config": self.config,
            "metadata": self.job_metadata,  # Map back to 'metadata' for API compatibility
        }

    @classmethod
    def from_request_data(cls, request_config: Dict[str, Any]):
        """Create Job from API request data"""
        # Extract required fields
        scan_id = request_config["scanId"]
        organization_id = request_config["organizationId"]
        job_type = request_config["type"][0] if request_config.get("type") else "user"

        # Store complete configuration
        complete_config = {
            "auth": request_config.get("auth", {}),
            "filters": request_config.get("filters", {}),
            "type": request_config.get("type", ["user"]),
        }

        return cls(
            id=scan_id,
            organizationId=organization_id,
            type=job_type,
            config=complete_config,
        )

    def get_latest_checkpoint(self):
        """Get the most recent checkpoint for this job"""
        if self.checkpoints:
            return max(self.checkpoints, key=lambda cp: cp.createdAt)
        return None


class JobCheckpoint(Base):
    __tablename__ = "job_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(255), ForeignKey("jobs.id"), nullable=False, index=True)
    createdAt = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Progress tracking
    phase = Column(String(50), nullable=False)  # e.g., 'users', 'teams', 'properties'
    recordsProcessed = Column(Integer, default=0)
    totalEstimated = Column(Integer, nullable=True)  # If known

    # Pagination state
    cursor = Column(String(500), nullable=True)  # API cursor/token for next page
    pageNumber = Column(Integer, default=0)
    batchSize = Column(Integer, default=100)

    # Data boundaries (for time-based resume)
    lastProcessedId = Column(String(255), nullable=True)
    lastProcessedTimestamp = Column(DateTime(timezone=True), nullable=True)

    # Additional context
    checkpoint_data = Column(
        JSON, nullable=True
    )  # Flexible storage for phase-specific data

    # Relationship back to job
    job = relationship("Job", back_populates="checkpoints")

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
            "phase": self.phase,
            "recordsProcessed": self.recordsProcessed,
            "totalEstimated": self.totalEstimated,
            "cursor": self.cursor,
            "pageNumber": self.pageNumber,
            "batchSize": self.batchSize,
            "lastProcessedId": self.lastProcessedId,
            "lastProcessedTimestamp": (
                self.lastProcessedTimestamp.isoformat()
                if self.lastProcessedTimestamp
                else None
            ),
            "checkpoint_data": self.checkpoint_data,
            "progress_percentage": self.get_progress_percentage(),
        }

    def get_progress_percentage(self) -> Optional[float]:
        """Calculate progress percentage if total is known"""
        if self.totalEstimated and self.totalEstimated > 0:
            return min(100.0, (self.recordsProcessed / self.totalEstimated) * 100.0)
        return None

    @classmethod
    def create_checkpoint(cls, job_id: str, phase: str, **kwargs):
        """Create a new checkpoint with common parameters"""
        return cls(
            job_id=job_id,
            phase=phase,
            recordsProcessed=kwargs.get("records_processed", 0),
            totalEstimated=kwargs.get("total_estimated"),
            cursor=kwargs.get("cursor"),
            pageNumber=kwargs.get("page_number", 0),
            batchSize=kwargs.get("batch_size", 100),
            lastProcessedId=kwargs.get("last_processed_id"),
            lastProcessedTimestamp=kwargs.get("last_processed_timestamp"),
            checkpoint_data=kwargs.get("checkpoint_data", {}),
        )


# User Jobs in case if one scan include jobs for multiple users
# class UserJob(Base):
#     __tablename__ = 'user_jobs'

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     job_id = Column(String(255), ForeignKey('jobs.id'), nullable=False, index=True)
#     user_id = Column(String(255), nullable=False, index=True)
#     status = Column(String(50), nullable=False, default=JobStatus.PENDING.value)
#     recordsExtracted = Column(Integer, default=0)
#     errorMessage = Column(Text, nullable=True)

#     def to_dict(self):
#         """Convert to dictionary for JSON serialization"""
#         return {
#             'id': self.id,
#             'job_id': self.job_id,
#             'user_id': self.user_id,
#             'status': self.status,
#             'recordsExtracted': self.recordsExtracted,
#             'errorMessage': self.errorMessage
#         }

#  User Jobs Checkpoint to track for checkpoint for a single user
# class UserJobCheckPoint
#     __tablename__ = 'user_job_checkpoints'

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     user_job_id = Column(Integer, ForeignKey('user_jobs.id'), nullable=False, index=True)
#     createdAt = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

#     # Progress tracking
#     phase = Column(String(50), nullable=False)  # e.g., 'users', 'teams', 'properties'
#     recordsProcessed = Column(Integer, default=0)
#     totalEstimated = Column(Integer, nullable=True)  # If known

#     # Pagination state
#     cursor = Column(String(500), nullable=True)  # API cursor/token for next page
#     pageNumber = Column(Integer, default=0)
#     batchSize = Column(Integer, default=100)

#     # Data boundaries (for time-based resume)
#     lastProcessedId = Column(String(255), nullable=True)
#     lastProcessedTimestamp = Column(DateTime(timezone=True), nullable=True)

#     # Additional context
#     checkpoint_data = Column(JSON, nullable=True)  # Flexible storage for phase-specific data

#     # Relationship back to user job
#     user_job = relationship("UserJob", back_populates="checkpoints")

#     def to_dict(self):
#         """Convert to dictionary for JSON serialization"""
#         return {
#             'id': self.id,
#             'user_job_id': self.user_job_id,
#             'createdAt': self.createdAt.isoformat() if self.createdAt else None,
#             'phase': self.phase,
#             'recordsProcessed': self.recordsProcessed,
#             'totalEstimated': self.totalEstimated,
#             'cursor': self.cursor,
#             'pageNumber': self.pageNumber,
#             'batchSize': self.batchSize,
#             'lastProcessedId': self.lastProcessedId,
#             'lastProcessedTimestamp': self.lastProcessedTimestamp.isoformat() if self.lastProcessedTimestamp else None,
#             'checkpoint_data': self.checkpoint_data,
#             'progress_percentage': self.get_progress_percentage()
#         }

#     def get_progress_percentage(self) -> Optional[float]:
#         """Calculate progress percentage if total is known"""
#         if self.totalEstimated and self.totalEstimated > 0:
#             return min(100.0, (self.recordsProcessed / self.totalEstimated) * 100.0)
#         return None

#     @classmethod
#     def create_checkpoint(cls, user_job_id: int, phase: str, **kwargs):
#         """Create a new checkpoint with common parameters"""
#         return cls(
#             user_job_id=user_job_id,
#             phase=phase,
#             recordsProcessed=kwargs.get('records_processed', 0),
#             totalEstimated=kwargs.get('total_estimated'),
#             cursor=kwargs.get('cursor'),
#             pageNumber=kwargs.get('page_number', 0),
#             batchSize=kwargs.get('batch_size', 100),
#             lastProcessedId=kwargs.get('last_processed_id'),
#             lastProcessedTimestamp=kwargs.get('last_processed_timestamp'),
#             checkpoint_data=kwargs.get('checkpoint_data', {})
#         )
