"""
Detection API Request/Response Schemas

Pydantic models for detection-related API endpoints:
- Scan requests
- Detection listings
- Detection details
"""

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.schemas.detection import ResourceType


class DetectionPayload(BaseModel):
    """Request payload for scanning resources"""

    resource_types: list[ResourceType] = Field(
        default_factory=lambda: [
            ResourceType.EC2_INSTANCE,
            ResourceType.EBS_VOLUME,
            ResourceType.EBS_SNAPSHOT,
        ],
        description="List of resource types to scan. Defaults to all types.",
    )

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "resource_types": ["ec2_instance", "ebs_volume"],
            }
        }


class DetectionResponse(BaseModel):
    """Response model for a single detection"""

    id: int
    resource_type: str
    resource_id: str
    resource_name: str | None
    region: str
    confidence_score: float
    estimated_monthly_savings_inr: float
    status: str
    approved_by: str | None
    approved_at: str | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "id": 1,
                "resource_type": "ec2_instance",
                "resource_id": "i-1234567890abcdef0",
                "resource_name": "my-idle-instance",
                "region": "us-east-1",
                "confidence_score": 0.95,
                "estimated_monthly_savings_inr": 2500.0,
                "status": "pending",
                "approved_by": None,
                "approved_at": None,
                "metadata": {
                    "avg_cpu_percent": 2.5,
                    "instance_type": "t3.medium",
                },
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }


class DetectionListResponse(BaseModel):
    """Response model for detection list"""

    detections: list[DetectionResponse]
    total: int
    filtered: int

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "detections": [],
                "total": 50,
                "filtered": 10,
            }
        }


class ScanResponse(BaseModel):
    """Response model for scan operation"""

    message: str
    total_detections: int
    total_monthly_savings_inr: float
    detections_by_type: dict[str, int]
    scan_duration_seconds: float

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "message": "Scan completed successfully",
                "total_detections": 15,
                "total_monthly_savings_inr": 45000.0,
                "detections_by_type": {
                    "ec2_instance": 5,
                    "ebs_volume": 7,
                    "ebs_snapshot": 3,
                },
                "scan_duration_seconds": 12.5,
            }
        }


class SnapshotMetadata(BaseModel):
    """Optional snapshot-specific metadata enriched from live AWS data"""

    snapshot_age_days: int | None = None
    snapshot_size_gb: float | None = None
    linked_ami_id: str | None = None
    blocked_reason: str | None = None


class DetectionDetailResponse(BaseModel):
    """Response model for detection detail with preview"""

    detection: DetectionResponse
    action_preview: dict[str, Any]
    # Snapshot-specific fields (populated from live AWS data when resource_type == ebs_snapshot)
    snapshot_age_days: int | None = None
    snapshot_size_gb: float | None = None
    linked_ami_id: str | None = None

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "detection": {},
                "action_preview": {
                    "action_type": "stop_ec2_instance",
                    "resource_id": "i-1234567890abcdef0",
                    "estimated_impact": "Instance will be stopped",
                    "can_rollback": True,
                    "rollback_window_days": 7,
                },
                "snapshot_age_days": None,
                "snapshot_size_gb": None,
                "linked_ami_id": None,
            }
        }
