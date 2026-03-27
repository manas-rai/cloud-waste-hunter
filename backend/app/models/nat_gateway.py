"""
NAT Gateway Pydantic Models for API serialisation
"""

from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class NATGatewayResponse(BaseModel):
    """Response model for a NAT Gateway resource"""

    id: int
    nat_gateway_id: str
    vpc_id: str | None
    subnet_id: str | None
    state: str
    region: str
    account_id: str | None
    tags: dict[str, Any]
    first_seen_at: str | None
    last_seen_at: str | None
    created_at: str | None
    updated_at: str | None

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "id": 1,
                "nat_gateway_id": "nat-0a1b2c3d4e5f67890",
                "vpc_id": "vpc-0123456789abcdef0",
                "subnet_id": "subnet-0123456789abcdef0",
                "state": "available",
                "region": "us-east-1",
                "account_id": "123456789012",
                "tags": {"Name": "prod-nat-gateway"},
                "first_seen_at": "2025-01-01T00:00:00Z",
                "last_seen_at": "2025-01-08T00:00:00Z",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-08T00:00:00Z",
            }
        }


class NATGatewayMetricResponse(BaseModel):
    """Response model for a NAT Gateway CloudWatch metric data point"""

    id: int
    nat_gateway_id: str
    metric_name: str
    timestamp: str
    value: float
    unit: str | None

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "id": 1,
                "nat_gateway_id": "nat-0a1b2c3d4e5f67890",
                "metric_name": "BytesOutToDestination",
                "timestamp": "2025-01-07T12:00:00Z",
                "value": 1024.0,
                "unit": "Bytes",
            }
        }


class NATGatewayWasteCandidate(BaseModel):
    """Response model for a NAT Gateway flagged as a waste candidate"""

    resource_id: str
    resource_type: str = "nat_gateway"
    resource_name: str | None
    region: str
    reason: str
    total_bytes_out_7d: float
    avg_active_connections: float
    confidence_score: float
    estimated_monthly_cost_usd: float
    detected_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "resource_id": "nat-0a1b2c3d4e5f67890",
                "resource_type": "nat_gateway",
                "resource_name": "prod-nat-gateway",
                "region": "us-east-1",
                "reason": "NAT Gateway has near-zero traffic over the last 7 days",
                "total_bytes_out_7d": 0.0,
                "avg_active_connections": 0.0,
                "confidence_score": 0.95,
                "estimated_monthly_cost_usd": 32.4,
                "detected_at": "2025-01-08T00:00:00Z",
                "metadata": {"vpc_id": "vpc-0123456789abcdef0", "tags": {}},
            }
        }


class NATGatewayScanResponse(BaseModel):
    """Response model for a NAT Gateway scan"""

    total_gateways: int
    total_idle_candidates: int
    candidates: list[NATGatewayWasteCandidate]

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "total_gateways": 5,
                "total_idle_candidates": 2,
                "candidates": [],
            }
        }
