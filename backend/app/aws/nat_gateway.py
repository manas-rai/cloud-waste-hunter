"""
NAT Gateway Resource Discovery and CloudWatch Metrics Collection
"""

from datetime import UTC, datetime, timedelta

import structlog

from app.aws.client import AWSClientFactory

logger = structlog.get_logger()

NAT_GATEWAY_METRICS = [
    "BytesOutToDestination",
    "BytesOutToSource",
    "PacketsOutToDestination",
    "PacketsOutToSource",
    "ActiveConnectionCount",
]


class NATGatewayCollector:
    """Collect NAT Gateway inventory and CloudWatch metrics"""

    def __init__(self, client_factory: AWSClientFactory):
        self.ec2_client = client_factory.get_ec2_client()
        self.cloudwatch = client_factory.get_cloudwatch_client()

    def list_nat_gateways(self) -> list[dict]:
        """
        List all available NAT Gateways in the region.

        Returns:
            List of NAT Gateway dicts with id, vpc_id, subnet_id, state, region, tags
        """
        gateways = []
        paginator = self.ec2_client.get_paginator("describe_nat_gateways")

        for page in paginator.paginate(
            Filters=[{"Name": "state", "Values": ["available"]}]
        ):
            for gw in page["NatGateways"]:
                gateways.append(
                    {
                        "nat_gateway_id": gw["NatGatewayId"],
                        "vpc_id": gw.get("VpcId"),
                        "subnet_id": gw.get("SubnetId"),
                        "state": gw["State"],
                        "region": self.ec2_client.meta.region_name,
                        "create_time": gw.get("CreateTime"),
                        "tags": {
                            tag["Key"]: tag["Value"] for tag in gw.get("Tags", [])
                        },
                    }
                )

        logger.info("NAT Gateways discovered", count=len(gateways))
        return gateways

    def get_nat_gateway_metrics(
        self, nat_gateway_id: str, days: int = 7
    ) -> list[dict]:
        """
        Collect CloudWatch metrics for a NAT Gateway over a rolling window.

        Args:
            nat_gateway_id: The NAT Gateway ID
            days: Number of days to look back (default 7)

        Returns:
            List of metric data dicts with metric_name, timestamp, value, unit
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        results = []

        for metric_name in NAT_GATEWAY_METRICS:
            # Use Sum for byte/packet metrics, Average for connection counts
            statistic = (
                "Average" if metric_name == "ActiveConnectionCount" else "Sum"
            )

            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace="AWS/NATGateway",
                    MetricName=metric_name,
                    Dimensions=[
                        {"Name": "NatGatewayId", "Value": nat_gateway_id}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # hourly
                    Statistics=[statistic],
                )

                for datapoint in response.get("Datapoints", []):
                    results.append(
                        {
                            "nat_gateway_id": nat_gateway_id,
                            "metric_name": metric_name,
                            "timestamp": datapoint["Timestamp"],
                            "value": datapoint[statistic],
                            "unit": datapoint.get("Unit", "None"),
                        }
                    )

            except Exception as e:
                logger.warning(
                    "Error fetching NAT Gateway metric",
                    nat_gateway_id=nat_gateway_id,
                    metric_name=metric_name,
                    error=str(e),
                )

        return results
