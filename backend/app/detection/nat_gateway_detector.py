"""
NAT Gateway Idle Detection
"""

from datetime import UTC, datetime

import structlog

logger = structlog.get_logger()

IDLE_THRESHOLD_BYTES = 1_073_741_824  # 1 GB in bytes


class NatGatewayDetector:
    """
    Detect idle NAT Gateways

    Criteria:
    - BytesOutToDestination + BytesInFromDestination < 1 GB over 7 days
    """

    def detect(self, nat_gateways: list[dict]) -> list[dict]:
        """
        Detect idle NAT Gateways based on traffic thresholds

        Args:
            nat_gateways: List of NAT Gateway dicts containing inventory
                          fields merged with CloudWatch metrics

        Returns:
            List of detection dicts for idle NAT Gateways
        """
        detections = []

        for gw in nat_gateways:
            nat_gateway_id = gw.get("nat_gateway_id", "")
            bytes_out = gw.get("bytes_out_7d") or 0.0
            bytes_in = gw.get("bytes_in_7d") or 0.0
            total_bytes = bytes_out + bytes_in

            if total_bytes >= IDLE_THRESHOLD_BYTES:
                continue  # Active gateway — skip

            # Confidence proportional to how far below the threshold we are:
            # 0 bytes → confidence 1.0, bytes at threshold → confidence 0.0
            confidence = 1.0 - (total_bytes / IDLE_THRESHOLD_BYTES)
            confidence = round(min(max(confidence, 0.0), 1.0), 3)

            savings = self._estimate_savings()

            detections.append(
                {
                    "resource_type": "nat_gateway",
                    "resource_id": nat_gateway_id,
                    "resource_name": gw.get("tags", {}).get("Name", nat_gateway_id),
                    "region": gw.get("region", ""),
                    "confidence_score": confidence,
                    "estimated_monthly_savings_inr": savings,
                    "detected_at": datetime.now(UTC).isoformat(),
                    "metadata": {
                        "vpc_id": gw.get("vpc_id"),
                        "subnet_id": gw.get("subnet_id"),
                        "bytes_out_7d": bytes_out,
                        "bytes_in_7d": bytes_in,
                        "total_bytes_7d": total_bytes,
                        "active_connections_avg": gw.get("active_connections_avg", 0.0),
                        "packets_out_7d": gw.get("packets_out_7d", 0.0),
                        "tags": gw.get("tags", {}),
                        "waste_reason": "Idle NAT Gateway: < 1 GB traffic over 7 days",
                    },
                }
            )

        logger.info(
            "NAT Gateway idle detection complete",
            total_gateways=len(nat_gateways),
            idle_detected=len(detections),
        )

        return detections

    def _estimate_savings(self) -> float:
        """
        Estimate monthly savings in INR for removing this NAT Gateway

        NAT Gateway pricing (ap-south-1 / Mumbai):
        - ~$0.045/hour ≈ ₹3.75/hour at 83 INR/USD
        - Monthly ≈ ₹2,700 (excluding data-processing charges)
        """
        hourly_rate_inr = 3.75
        monthly_cost = hourly_rate_inr * 24 * 30
        return round(monthly_cost, 2)
