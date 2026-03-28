"""
NAT Gateway Idle Detection
"""

from datetime import UTC, datetime, timedelta

import structlog

from app.core.config import settings
from app.models.detection_models import NatGatewayDetectionModel

logger = structlog.get_logger()


class NatGatewayDetector:
    """
    Detect idle NAT Gateways based on CloudWatch traffic metrics

    Criteria:
    - Total bytes processed (in + out) < threshold over lookback window
    """

    def __init__(
        self,
        threshold_bytes: int | None = None,
        lookback_days: int | None = None,
    ):
        self.threshold_bytes = (
            threshold_bytes
            if threshold_bytes is not None
            else settings.NAT_GATEWAY_IDLE_BYTES_THRESHOLD
        )
        self.lookback_days = (
            lookback_days
            if lookback_days is not None
            else settings.NAT_GATEWAY_LOOKBACK_DAYS
        )

    def collect_metrics(self, nat_gw_id: str, region: str, cw_client) -> dict:
        """
        Collect CloudWatch traffic metrics for a NAT Gateway

        Args:
            nat_gw_id: NAT Gateway ID
            region: AWS region
            cw_client: Boto3 CloudWatch client

        Returns:
            Dict with bytes_in, bytes_out, total_bytes
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=self.lookback_days)

        def _get_metric_sum(metric_name: str) -> float:
            try:
                response = cw_client.get_metric_statistics(
                    Namespace="AWS/NATGateway",
                    MetricName=metric_name,
                    Dimensions=[{"Name": "NatGatewayId", "Value": nat_gw_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,  # 1 day periods
                    Statistics=["Sum"],
                )
                datapoints = response.get("Datapoints", [])
                if not datapoints:
                    return 0.0
                return sum(dp.get("Sum", 0.0) for dp in datapoints)
            except Exception as e:
                logger.warning(
                    "Error fetching NAT Gateway metric",
                    nat_gw_id=nat_gw_id,
                    metric=metric_name,
                    error=str(e),
                )
                return 0.0

        bytes_in = _get_metric_sum("BytesInFromSource")
        bytes_out = _get_metric_sum("BytesOutToDestination")
        total_bytes = bytes_in + bytes_out

        return {
            "bytes_in": bytes_in,
            "bytes_out": bytes_out,
            "total_bytes": total_bytes,
        }

    def detect(
        self,
        nat_gateways: list[dict],
        cw_client=None,
    ) -> list[NatGatewayDetectionModel]:
        """
        Detect idle NAT Gateways

        Args:
            nat_gateways: List of NAT Gateway dicts from list_nat_gateways()
            cw_client: Boto3 CloudWatch client (required unless overriding for tests)

        Returns:
            List of NatGatewayDetectionModel instances
        """
        detections = []

        for ngw in nat_gateways:
            nat_gw_id = ngw["id"]
            region = ngw.get("region", settings.AWS_REGION)

            if cw_client is not None:
                metrics = self.collect_metrics(nat_gw_id, region, cw_client)
            else:
                # No client provided: treat as idle (missing data)
                metrics = {"bytes_in": 0.0, "bytes_out": 0.0, "total_bytes": 0.0}

            total_bytes = metrics["total_bytes"]
            is_idle = total_bytes < self.threshold_bytes

            # waste_score: 1.0 = completely idle, 0.0 = at or above threshold
            if self.threshold_bytes > 0:
                waste_score = max(
                    0.0, 1.0 - (total_bytes / self.threshold_bytes)
                )
            else:
                waste_score = 1.0 if is_idle else 0.0

            waste_score = round(min(waste_score, 1.0), 4)

            detections.append(
                NatGatewayDetectionModel(
                    resource_id=nat_gw_id,
                    region=region,
                    account_id=ngw.get("account_id"),
                    vpc_id=ngw.get("vpc_id"),
                    subnet_id=ngw.get("subnet_id"),
                    bytes_in_7d=metrics["bytes_in"],
                    bytes_out_7d=metrics["bytes_out"],
                    total_bytes_7d=total_bytes,
                    is_idle=is_idle,
                    waste_score=waste_score,
                    detected_at=datetime.now(UTC).isoformat(),
                )
            )

            logger.info(
                "NAT Gateway detection",
                nat_gw_id=nat_gw_id,
                total_bytes=total_bytes,
                is_idle=is_idle,
                waste_score=waste_score,
            )

        return detections
