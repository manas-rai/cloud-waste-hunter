"""
Pydantic Models for API Request/Response Validation

This package contains all Pydantic models used for:
- Request validation
- Response serialization
- API documentation
"""

from app.models.action_models import (
    ApprovalRequest,
    BatchApprovalRequest,
    BatchRejectRequest,
    ApprovalResponse,
    BatchOperationResult,
    BatchOperationResponse,
)
from app.models.detection_models import (
    DetectionPayload,
    DetectionResponse,
    DetectionListResponse,
    ScanResponse,
    DetectionDetailResponse,
)
from app.models.audit_models import (
    RollbackRequest,
    AuditLogResponse,
    AuditLogsResponse,
    RollbackResponse,
)

__all__ = [
    # Action models
    "ApprovalRequest",
    "BatchApprovalRequest",
    "BatchRejectRequest",
    "ApprovalResponse",
    "BatchOperationResult",
    "BatchOperationResponse",
    # Detection models
    "DetectionPayload",
    "DetectionResponse",
    "DetectionListResponse",
    "ScanResponse",
    "DetectionDetailResponse",
    # Audit models
    "RollbackRequest",
    "AuditLogResponse",
    "AuditLogsResponse",
    "RollbackResponse",
]
