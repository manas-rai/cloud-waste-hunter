"""
NAT Gateway Inventory and CloudWatch Metrics Collection
"""

from datetime import UTC, datetime, timedelta

import structlog

from app.aws.client import AWSClientFactory

logger = structlog.get_logger()


class NATGatewayCollector:
    """Collect NAT Gateway inventory and CloudWatch metrics"""

    def __init__(self, client_factory: AWSClientFactory):
        self.ec2_client = client_factory.get_ec2_client()
        self.cloudwatch = client_factory.get_cloudwatch_client()

    def get_all_nat_gateways(self) -> list[dict]:
        """
        Get all available NAT Gateways

        Returns:
            List of NAT Gateway dictionaries with metadata
        """
        nat_gateways = []
        paginator = self.ec2_client.get_paginator("describe_nat_gateways")

        for page in paginator.paginate(
            Filters=[{"Name": "state", "Values": ["available"]}]
        ):
            for gw in page["NatGateways"]:
                nat_gateways.append(
                    {
                        "nat_gateway_id": gw["NatGatewayId"],
                        "subnet_id": gw.get("SubnetId"),
                        "vpc_id": gw.get("VpcId"),
                        "state": gw["State"],
                        "create_time": gw.get("CreateTime"),
                        "tags": {
                            tag["Key"]: tag["Value"]
                            for tag in gw.get("Tags", [])
                        },
                        "region": self.ec2_client.meta.region_name,
                    }
                )

        return nat_gateways

    def get_nat_gateway_metrics(
        self, nat_gateway_id: str, lookback_days: int = 7
    ) -> dict:
        """
        Get CloudWatch metrics for a NAT Gateway over the lookback window

        Args:
            nat_gateway_id: NAT Gateway ID
            lookback_days: Number of days to look back (default 7)

        Returns:
            Dict with aggregated metric totals/averages
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=lookback_days)
        period = 86400  # Daily periods

        dimensions = [{"Name": "NatGatewayId", "Value": nat_gateway_id}]

        def _sum_metric(metric_name: str) -> float:
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace="AWS/NATGateway",
                    MetricName=metric_name,
                    Dimensions=dimensions,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=period,
                    Statistics=["Sum"],
                )
                return sum(dp["Sum"] for dp in response.get("Datapoints", []))
            except Exception as e:
                logger.warning(
                    "Error fetching NAT Gateway sum metric",
                    nat_gateway_id=nat_gateway_id,
                    metric=metric_name,
                    error=str(e),
                )
                return 0.0

        def _avg_metric(metric_name: str) -> float:
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace="AWS/NATGateway",
                    MetricName=metric_name,
                    Dimensions=dimensions,
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=period,
                    Statistics=["Average"],
                )
                datapoints = response.get("Datapoints", [])
                if not datapoints:
                    return 0.0
                return sum(dp["Average"] for dp in datapoints) / len(datapoints)
            except Exception as e:
                logger.warning(
                    "Error fetching NAT Gateway average metric",
                    nat_gateway_id=nat_gateway_id,
                    metric=metric_name,
                    error=str(e),
                )
                return 0.0

        return {
            "bytes_out_7d": _sum_metric("BytesOutToDestination"),
            "bytes_in_7d": _sum_metric("BytesInFromDestination"),
            "active_connections_avg": _avg_metric("ActiveConnectionCount"),
            "packets_out_7d": _sum_metric("PacketsOutToDestination"),
        }
