"""
Detection Database Schema (SQLAlchemy Model)
"""

import enum

from sqlalchemy import JSON, Column, DateTime, Enum, Float, Integer, String

from app.schemas.base import Base, TimestampMixin


class ResourceType(str, enum.Enum):
    """Resource types we detect"""

    EC2_INSTANCE = "ec2_instance"
    EBS_VOLUME = "ebs_volume"
    EBS_SNAPSHOT = "ebs_snapshot"
    NAT_GATEWAY = "nat_gateway"


class DetectionStatus(str, enum.Enum):
    """Detection status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class Detection(Base, TimestampMixin):
    """Detection database model (table)"""

    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(Enum(ResourceType), nullable=False, index=True)
    resource_id = Column(String(255), nullable=False, index=True)
    resource_name = Column(String(255))
    region = Column(String(50), nullable=False)

    # Detection metrics
    confidence_score = Column(Float, nullable=False)
    estimated_monthly_savings_inr = Column(Float, nullable=False)

    # Status and workflow
    status = Column(Enum(DetectionStatus), default=DetectionStatus.PENDING, index=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata (JSON field for flexible data)
    # Note: Using 'meta_data' instead of 'metadata' because 'metadata' is reserved by SQLAlchemy
    meta_data = Column(JSON, default={}, name="metadata")

    # Detection-specific fields (stored in metadata or as separate columns)
    # For EC2: avg_cpu_percent, days_idle
    # For EBS: size_gb, age_days
    # For Snapshots: size_gb, age_days

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "resource_type": self.resource_type.value if self.resource_type else None,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "region": self.region,
            "confidence_score": self.confidence_score,
            "estimated_monthly_savings_inr": self.estimated_monthly_savings_inr,
            "status": self.status.value if self.status else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "metadata": self.meta_data,  # API uses 'metadata', column is 'meta_data'
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
