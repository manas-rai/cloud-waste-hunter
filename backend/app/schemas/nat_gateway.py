"""
NAT Gateway Database Schema (SQLAlchemy Models)
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.schemas.base import Base, TimestampMixin


class NATGateway(Base, TimestampMixin):
    """NAT Gateway inventory table"""

    __tablename__ = "nat_gateways"

    id = Column(Integer, primary_key=True, index=True)
    nat_gateway_id = Column(String(64), unique=True, nullable=False, index=True)
    vpc_id = Column(String(64), nullable=True)
    subnet_id = Column(String(64), nullable=True)
    state = Column(String(32), nullable=False)
    region = Column(String(50), nullable=False, index=True)
    account_id = Column(String(32), nullable=True)
    raw_tags = Column(JSONB, default={})
    first_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    metrics = relationship(
        "NATGatewayMetric",
        back_populates="gateway",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nat_gateway_id": self.nat_gateway_id,
            "vpc_id": self.vpc_id,
            "subnet_id": self.subnet_id,
            "state": self.state,
            "region": self.region,
            "account_id": self.account_id,
            "tags": self.raw_tags,
            "first_seen_at": (
                self.first_seen_at.isoformat() if self.first_seen_at else None
            ),
            "last_seen_at": (
                self.last_seen_at.isoformat() if self.last_seen_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NATGatewayMetric(Base):
    """NAT Gateway CloudWatch metrics time-series table"""

    __tablename__ = "nat_gateway_metrics"

    id = Column(Integer, primary_key=True, index=True)
    nat_gateway_id = Column(
        String(64),
        ForeignKey("nat_gateways.nat_gateway_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name = Column(String(64), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(32), nullable=True)

    gateway = relationship("NATGateway", back_populates="metrics")
