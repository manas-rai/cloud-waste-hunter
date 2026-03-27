"""
NAT Gateway Service - Orchestrates scan, persistence, and detection
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.aws.client import AWSClientFactory
from app.aws.nat_gateway import NATGatewayCollector
from app.detection.nat_gateway_detector import NATGatewayDetector
from app.repositories.nat_gateway_repository import nat_gateway_repository

logger = structlog.get_logger()


class NATGatewayService:
    """
    Orchestrates the full NAT Gateway scan workflow:
      1. Discover gateways via EC2 API
      2. Collect CloudWatch metrics
      3. Persist inventory + metrics to DB
      4. Run idle detection
      5. Return structured results
    """

    async def run_scan(
        self,
        db: AsyncSession,
        account_id: str | None = None,
        client_factory: AWSClientFactory | None = None,
    ) -> dict:
        """
        Execute a full NAT Gateway scan.

        Args:
            db: Async database session
            account_id: AWS account ID (informational, stored with each record)
            client_factory: Optional AWS client factory (for testing / DI)

        Returns:
            Dict with total_gateways, total_idle_candidates, and candidates list
        """
        if client_factory is None:
            client_factory = AWSClientFactory()

        collector = NATGatewayCollector(client_factory)
        detector = NATGatewayDetector()

        logger.info("Starting NAT Gateway scan", account_id=account_id)

        # 1. Discover gateways
        gateways = collector.list_nat_gateways()
        logger.info("NAT Gateways discovered", count=len(gateways))

        # 2. Collect metrics and persist everything
        metrics_by_gateway: dict[str, list[dict]] = {}

        for gw in gateways:
            gw["account_id"] = account_id

            # Persist / upsert inventory
            await nat_gateway_repository.upsert(db, gw)

            # Collect metrics
            metrics = collector.get_nat_gateway_metrics(gw["nat_gateway_id"])
            metrics_by_gateway[gw["nat_gateway_id"]] = metrics

            # Persist metrics
            await nat_gateway_repository.bulk_insert_metrics(db, metrics)

        # 3. Detect idle candidates
        candidates = detector.detect(gateways, metrics_by_gateway)

        logger.info(
            "NAT Gateway scan complete",
            total=len(gateways),
            idle_candidates=len(candidates),
        )

        return {
            "total_gateways": len(gateways),
            "total_idle_candidates": len(candidates),
            "candidates": candidates,
        }

    async def list_candidates(
        self,
        db: AsyncSession,
        client_factory: AWSClientFactory | None = None,
    ) -> dict:
        """
        Return idle NAT Gateway candidates based on persisted DB data.

        This does NOT re-scan AWS — it queries the stored metrics.
        """
        from app.core.config import settings

        candidates_db = await nat_gateway_repository.get_idle_candidates(
            db,
            bytes_threshold=settings.NAT_GATEWAY_IDLE_BYTES_THRESHOLD,
            conn_threshold=settings.NAT_GATEWAY_IDLE_CONNECTIONS_THRESHOLD,
        )

        detector = NATGatewayDetector()

        # Convert ORM rows to dicts and build light-weight candidate list
        results = []
        for gw in candidates_db:
            metrics = await nat_gateway_repository.get_metrics(
                db, gw.nat_gateway_id
            )
            metrics_dicts = [
                {
                    "nat_gateway_id": m.nat_gateway_id,
                    "metric_name": m.metric_name,
                    "timestamp": m.timestamp,
                    "value": m.value,
                    "unit": m.unit,
                }
                for m in metrics
            ]
            total_bytes, avg_conn = detector._aggregate_metrics(metrics_dicts)
            gw_dict = gw.to_dict()
            gw_dict["tags"] = gw.raw_tags or {}

            from datetime import UTC, datetime

            results.append(
                {
                    "resource_id": gw.nat_gateway_id,
                    "resource_type": "nat_gateway",
                    "resource_name": (gw.raw_tags or {}).get(
                        "Name", gw.nat_gateway_id
                    ),
                    "region": gw.region,
                    "reason": (
                        f"NAT Gateway has near-zero traffic over the last 7 days "
                        f"(bytes_out={total_bytes:.0f}, avg_connections={avg_conn:.2f})"
                    ),
                    "total_bytes_out_7d": total_bytes,
                    "avg_active_connections": avg_conn,
                    "confidence_score": 0.95,
                    "estimated_monthly_cost_usd": 32.4,
                    "detected_at": datetime.now(UTC).isoformat(),
                    "metadata": {
                        "vpc_id": gw.vpc_id,
                        "subnet_id": gw.subnet_id,
                        "tags": gw.raw_tags or {},
                    },
                }
            )

        return {
            "total_idle_candidates": len(results),
            "candidates": results,
        }

    async def get_candidate(
        self, db: AsyncSession, nat_gateway_id: str
    ) -> dict | None:
        """
        Return detail for a single NAT Gateway if it exists in the DB.
        """
        gw = await nat_gateway_repository.get_by_id(db, nat_gateway_id)
        if not gw:
            return None

        metrics = await nat_gateway_repository.get_metrics(db, nat_gateway_id)
        detector = NATGatewayDetector()
        metrics_dicts = [
            {
                "nat_gateway_id": m.nat_gateway_id,
                "metric_name": m.metric_name,
                "timestamp": m.timestamp,
                "value": m.value,
                "unit": m.unit,
            }
            for m in metrics
        ]
        total_bytes, avg_conn = detector._aggregate_metrics(metrics_dicts)
        is_idle = detector._is_idle(total_bytes, avg_conn)

        from datetime import UTC, datetime

        return {
            "resource_id": gw.nat_gateway_id,
            "resource_type": "nat_gateway",
            "resource_name": (gw.raw_tags or {}).get("Name", gw.nat_gateway_id),
            "region": gw.region,
            "is_idle": is_idle,
            "reason": (
                f"NAT Gateway has near-zero traffic over the last 7 days "
                f"(bytes_out={total_bytes:.0f}, avg_connections={avg_conn:.2f})"
            )
            if is_idle
            else "NAT Gateway has sufficient traffic — not flagged as idle",
            "total_bytes_out_7d": total_bytes,
            "avg_active_connections": avg_conn,
            "confidence_score": 0.95 if is_idle else 0.0,
            "estimated_monthly_cost_usd": 32.4,
            "detected_at": datetime.now(UTC).isoformat(),
            "metadata": {
                "vpc_id": gw.vpc_id,
                "subnet_id": gw.subnet_id,
                "tags": gw.raw_tags or {},
                "account_id": gw.account_id,
            },
        }


# Singleton instance
nat_gateway_service = NATGatewayService()
