"""
NAT Gateway Idle Detection

Flags a NAT Gateway as a waste candidate when:
  - Sum of BytesOutToDestination + BytesOutToSource over 7 days < NAT_GATEWAY_IDLE_BYTES_THRESHOLD
  - Average ActiveConnectionCount over 7 days < NAT_GATEWAY_IDLE_CONNECTIONS_THRESHOLD

Thresholds are pulled from app.core.config so they can be tuned without code changes.
"""

from datetime import UTC, datetime

import structlog

from app.core.config import settings

logger = structlog.get_logger()

# ~$32/month flat NAT Gateway charge (per gateway per region) used as cost placeholder
NAT_GATEWAY_MONTHLY_COST_USD = 32.4


class NATGatewayDetector:
    """
    Rule-based detector for idle NAT Gateways.

    Accepts pre-fetched metric data so it can be tested without live AWS calls.
    """

    def __init__(
        self,
        bytes_threshold: float | None = None,
        conn_threshold: float | None = None,
    ):
        self.bytes_threshold = (
            bytes_threshold
            if bytes_threshold is not None
            else settings.NAT_GATEWAY_IDLE_BYTES_THRESHOLD
        )
        self.conn_threshold = (
            conn_threshold
            if conn_threshold is not None
            else settings.NAT_GATEWAY_IDLE_CONNECTIONS_THRESHOLD
        )

    def detect(
        self,
        gateways: list[dict],
        metrics_by_gateway: dict[str, list[dict]],
    ) -> list[dict]:
        """
        Evaluate each gateway and return those that are idle.

        Args:
            gateways: List of gateway dicts (from NATGatewayCollector.list_nat_gateways)
            metrics_by_gateway: Mapping of nat_gateway_id → list of metric dicts

        Returns:
            List of waste-candidate dicts compatible with the detection result format
        """
        candidates = []

        for gw in gateways:
            gw_id = gw["nat_gateway_id"]
            metrics = metrics_by_gateway.get(gw_id, [])

            total_bytes_out, avg_connections = self._aggregate_metrics(metrics)

            if not self._is_idle(total_bytes_out, avg_connections):
                continue

            logger.info(
                "NAT Gateway flagged as idle",
                nat_gateway_id=gw_id,
                total_bytes_out=total_bytes_out,
                avg_connections=avg_connections,
            )

            candidates.append(
                {
                    "resource_id": gw_id,
                    "resource_type": "nat_gateway",
                    "resource_name": gw.get("tags", {}).get("Name", gw_id),
                    "region": gw["region"],
                    "reason": (
                        f"NAT Gateway has near-zero traffic over the last 7 days "
                        f"(bytes_out={total_bytes_out:.0f}, avg_connections={avg_connections:.2f})"
                    ),
                    "total_bytes_out_7d": total_bytes_out,
                    "avg_active_connections": avg_connections,
                    "confidence_score": 0.95,
                    "estimated_monthly_cost_usd": NAT_GATEWAY_MONTHLY_COST_USD,
                    "detected_at": datetime.now(UTC).isoformat(),
                    "metadata": {
                        "vpc_id": gw.get("vpc_id"),
                        "subnet_id": gw.get("subnet_id"),
                        "tags": gw.get("tags", {}),
                        "bytes_threshold": self.bytes_threshold,
                        "conn_threshold": self.conn_threshold,
                    },
                }
            )

        return candidates

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _aggregate_metrics(self, metrics: list[dict]) -> tuple[float, float]:
        """
        Compute:
          - total_bytes_out: sum of BytesOutToDestination + BytesOutToSource
          - avg_connections: mean of ActiveConnectionCount

        Returns:
            (total_bytes_out, avg_connections)
        """
        bytes_values = [
            m["value"]
            for m in metrics
            if m["metric_name"] in ("BytesOutToDestination", "BytesOutToSource")
        ]
        conn_values = [
            m["value"]
            for m in metrics
            if m["metric_name"] == "ActiveConnectionCount"
        ]

        total_bytes_out = sum(bytes_values)
        avg_connections = (
            sum(conn_values) / len(conn_values) if conn_values else 0.0
        )

        return total_bytes_out, avg_connections

    def _is_idle(self, total_bytes_out: float, avg_connections: float) -> bool:
        """Return True when both thresholds indicate idle."""
        return (
            total_bytes_out < self.bytes_threshold
            and avg_connections < self.conn_threshold
        )
