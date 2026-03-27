"""
NAT Gateway Repository - Data access for NATGateway and NATGatewayMetric models
"""

from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.nat_gateway import NATGateway, NATGatewayMetric

logger = structlog.get_logger()


class NATGatewayRepository:
    """
    Repository for NAT Gateway data access.

    Encapsulates all database operations for NATGateway and NATGatewayMetric.
    """

    async def upsert(
        self, db: AsyncSession, gateway_data: dict
    ) -> NATGateway:
        """
        Insert or update a NAT Gateway record.

        Uses PostgreSQL ON CONFLICT DO UPDATE to handle re-scans gracefully.
        """
        now = datetime.now(UTC)

        stmt = (
            insert(NATGateway)
            .values(
                nat_gateway_id=gateway_data["nat_gateway_id"],
                vpc_id=gateway_data.get("vpc_id"),
                subnet_id=gateway_data.get("subnet_id"),
                state=gateway_data.get("state", "available"),
                region=gateway_data["region"],
                account_id=gateway_data.get("account_id"),
                raw_tags=gateway_data.get("tags", {}),
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["nat_gateway_id"],
                set_={
                    "state": gateway_data.get("state", "available"),
                    "raw_tags": gateway_data.get("tags", {}),
                    "last_seen_at": now,
                    "updated_at": now,
                },
            )
            .returning(NATGateway)
        )

        result = await db.execute(stmt)
        await db.flush()
        row = result.scalar_one()
        return row

    async def bulk_insert_metrics(
        self, db: AsyncSession, metrics: list[dict]
    ) -> int:
        """
        Bulk insert metric data points.

        Args:
            db: Database session
            metrics: List of metric dicts from the collector

        Returns:
            Number of rows inserted
        """
        if not metrics:
            return 0

        rows = [
            NATGatewayMetric(
                nat_gateway_id=m["nat_gateway_id"],
                metric_name=m["metric_name"],
                timestamp=m["timestamp"],
                value=m["value"],
                unit=m.get("unit"),
            )
            for m in metrics
        ]

        db.add_all(rows)
        await db.flush()
        logger.info("Inserted NAT Gateway metrics", count=len(rows))
        return len(rows)

    async def list_all(
        self, db: AsyncSession, region: str | None = None
    ) -> list[NATGateway]:
        """Return all NAT Gateways, optionally filtered by region."""
        stmt = select(NATGateway)
        if region:
            stmt = stmt.where(NATGateway.region == region)
        stmt = stmt.order_by(NATGateway.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self, db: AsyncSession, nat_gateway_id: str
    ) -> NATGateway | None:
        """Fetch a single NAT Gateway by its AWS resource ID."""
        stmt = select(NATGateway).where(
            NATGateway.nat_gateway_id == nat_gateway_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_metrics(
        self,
        db: AsyncSession,
        nat_gateway_id: str,
        metric_name: str | None = None,
    ) -> list[NATGatewayMetric]:
        """Fetch stored metric rows for a given NAT Gateway."""
        stmt = select(NATGatewayMetric).where(
            NATGatewayMetric.nat_gateway_id == nat_gateway_id
        )
        if metric_name:
            stmt = stmt.where(NATGatewayMetric.metric_name == metric_name)
        stmt = stmt.order_by(NATGatewayMetric.timestamp.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_idle_candidates(
        self,
        db: AsyncSession,
        bytes_threshold: float,
        conn_threshold: float,
    ) -> list[NATGateway]:
        """
        Return NAT Gateways whose stored metrics indicate idle behaviour.

        Idle = sum(BytesOutToDestination + BytesOutToSource) < bytes_threshold
               AND avg(ActiveConnectionCount) < conn_threshold
        """
        # Subquery: total bytes out per gateway
        bytes_sub = (
            select(
                NATGatewayMetric.nat_gateway_id,
                func.coalesce(func.sum(NATGatewayMetric.value), 0).label(
                    "total_bytes"
                ),
            )
            .where(
                NATGatewayMetric.metric_name.in_(
                    ["BytesOutToDestination", "BytesOutToSource"]
                )
            )
            .group_by(NATGatewayMetric.nat_gateway_id)
            .subquery()
        )

        # Subquery: avg active connections per gateway
        conn_sub = (
            select(
                NATGatewayMetric.nat_gateway_id,
                func.coalesce(func.avg(NATGatewayMetric.value), 0).label(
                    "avg_connections"
                ),
            )
            .where(
                NATGatewayMetric.metric_name == "ActiveConnectionCount"
            )
            .group_by(NATGatewayMetric.nat_gateway_id)
            .subquery()
        )

        stmt = (
            select(NATGateway)
            .join(
                bytes_sub,
                NATGateway.nat_gateway_id == bytes_sub.c.nat_gateway_id,
                isouter=True,
            )
            .join(
                conn_sub,
                NATGateway.nat_gateway_id == conn_sub.c.nat_gateway_id,
                isouter=True,
            )
            .where(
                func.coalesce(bytes_sub.c.total_bytes, 0) < bytes_threshold
            )
            .where(
                func.coalesce(conn_sub.c.avg_connections, 0) < conn_threshold
            )
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())


# Singleton instance
nat_gateway_repository = NATGatewayRepository()
