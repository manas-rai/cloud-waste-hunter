"""
NAT Gateway Database Schema (SQLAlchemy Model)
"""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from app.schemas.base import Base, TimestampMixin


class NatGateway(Base, TimestampMixin):
    """NAT Gateway inventory and aggregated metrics table"""

    __tablename__ = "nat_gateways"

    id = Column(Integer, primary_key=True, index=True)
    nat_gateway_id = Column(String(50), unique=True, nullable=False, index=True)
    vpc_id = Column(String(50))
    subnet_id = Column(String(50))
    state = Column(String(20))
    create_time = Column(DateTime(timezone=True))

    # Aggregated CloudWatch metrics over 7-day window
    bytes_out_7d = Column(Float, default=0.0)
    bytes_in_7d = Column(Float, default=0.0)
    active_connections_avg = Column(Float, default=0.0)
    packets_out_7d = Column(Float, default=0.0)

    tags = Column(JSON, default={})
    scanned_at = Column(DateTime(timezone=True))
    account_id = Column(String(50))
