"""
Audit Log API Request/Response Schemas

Pydantic models for audit-related API endpoints:
- Rollback requests
- Audit log listings
- Audit log details
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class RollbackRequest(BaseModel):
    """Request model for rolling back an action"""

    rolled_back_by: str = Field(..., description="Email or ID of user performing the rollback")


class AuditLogResponse(BaseModel):
    """Response model for a single audit log"""

    id: int
    detection_id: Optional[int]
    action_type: str
    resource_type: str
    resource_id: str
    status: str
    executed_by: str
    executed_at: str
    dry_run: bool
    can_rollback: bool
    rolled_back_at: Optional[str]
    rolled_back_by: Optional[str]
    error_message: Optional[str]
    meta_data: Dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "detection_id": 10,
                "action_type": "stop_ec2_instance",
                "resource_type": "ec2_instance",
                "resource_id": "i-1234567890abcdef0",
                "status": "SUCCESS",
                "executed_by": "user@example.com",
                "executed_at": "2025-01-01T12:00:00Z",
                "dry_run": False,
                "can_rollback": True,
                "rolled_back_at": None,
                "rolled_back_by": None,
                "error_message": None,
                "meta_data": {
                    "previous_state": "running",
                    "instance_type": "t3.medium",
                },
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
            }
        }


class AuditLogsResponse(BaseModel):
    """Response model for audit logs list"""

    logs: List[AuditLogResponse]
    total: int
    limit: int
    offset: int

    class Config:
        json_schema_extra = {
            "example": {
                "logs": [],
                "total": 100,
                "limit": 20,
                "offset": 0,
            }
        }


class RollbackResponse(BaseModel):
    """Response model for rollback operation"""

    message: str
    audit_log: AuditLogResponse
    rollback_action: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Rollback successful",
                "audit_log": {},
                "rollback_action": {
                    "action_type": "start_ec2_instance",
                    "resource_id": "i-1234567890abcdef0",
                    "status": "SUCCESS",
                },
            }
        }

