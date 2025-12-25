"""
Audit Log Database Schema (SQLAlchemy Model)
"""

import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from app.schemas.base import Base, TimestampMixin


class ActionType(str, enum.Enum):
    """Action types"""

    STOP_EC2 = "stop_ec2_instance"
    DELETE_EBS_VOLUME = "delete_ebs_volume"
    DELETE_SNAPSHOT = "delete_ebs_snapshot"
    ROLLBACK = "rollback"


class AuditStatus(str, enum.Enum):
    """Audit log status"""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class AuditLog(Base, TimestampMixin):
    """Audit log database model (table)"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(
        Integer, ForeignKey("detections.id"), nullable=True, index=True
    )

    action_type = Column(Enum(ActionType), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255), nullable=False, index=True)

    status = Column(Enum(AuditStatus), default=AuditStatus.PENDING, index=True)

    # Who and when
    executed_by = Column(String(255), nullable=False)
    executed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Execution details
    dry_run = Column(Boolean, default=False)
    result = Column(JSON, default={})  # Store execution result
    error_message = Column(Text, nullable=True)

    # Rollback info
    can_rollback = Column(Boolean, default=False)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_by = Column(String(255), nullable=True)

    # Additional metadata
    # Note: Using 'meta_data' instead of 'metadata' because 'metadata' is reserved by SQLAlchemy
    meta_data = Column(JSON, default={}, name="metadata")

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "detection_id": self.detection_id,
            "action_type": self.action_type.value if self.action_type else None,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "status": self.status.value if self.status else None,
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "dry_run": self.dry_run,
            "result": self.result,
            "error_message": self.error_message,
            "can_rollback": self.can_rollback,
            "rolled_back_at": (
                self.rolled_back_at.isoformat() if self.rolled_back_at else None
            ),
            "rolled_back_by": self.rolled_back_by,
            "metadata": self.meta_data,  # API uses 'metadata', column is 'meta_data'
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
