"""
Unit tests for NATGatewayCollector (inventory + CloudWatch metrics)
"""

from unittest.mock import MagicMock, patch

import pytest

from app.aws.nat_gateway import NATGatewayCollector


def _make_client_factory(ec2_responses=None, cw_responses=None):
    """Build a mock AWSClientFactory."""
    factory = MagicMock()

    # EC2 client
    ec2 = MagicMock()
    ec2.meta.region_name = "ap-south-1"
    paginator = MagicMock()
    paginator.paginate.return_value = ec2_responses or [{"NatGateways": []}]
    ec2.get_paginator.return_value = paginator
    factory.get_ec2_client.return_value = ec2

    # CloudWatch client
    cw = MagicMock()
    cw.get_metric_statistics.return_value = cw_responses or {"Datapoints": []}
    factory.get_cloudwatch_client.return_value = cw

    return factory, ec2, cw


class TestGetAllNatGateways:
    def test_returns_empty_list_when_no_gateways(self):
        factory, _, _ = _make_client_factory()
        collector = NATGatewayCollector(factory)
        result = collector.get_all_nat_gateways()
        assert result == []

    def test_filters_to_available_state(self):
        factory, ec2, _ = _make_client_factory()
        collector = NATGatewayCollector(factory)
        collector.get_all_nat_gateways()
        paginator = ec2.get_paginator.return_value
        paginator.paginate.assert_called_once_with(
            Filters=[{"Name": "state", "Values": ["available"]}]
        )

    def test_maps_gateway_fields(self):
        gw = {
            "NatGatewayId": "nat-abc123",
            "SubnetId": "subnet-1",
            "VpcId": "vpc-1",
            "State": "available",
            "CreateTime": "2025-01-01T00:00:00+00:00",
            "Tags": [{"Key": "Name", "Value": "my-gw"}],
        }
        factory, _, _ = _make_client_factory(
            ec2_responses=[{"NatGateways": [gw]}]
        )
        collector = NATGatewayCollector(factory)
        result = collector.get_all_nat_gateways()
        assert len(result) == 1
        assert result[0]["nat_gateway_id"] == "nat-abc123"
        assert result[0]["subnet_id"] == "subnet-1"
        assert result[0]["vpc_id"] == "vpc-1"
        assert result[0]["state"] == "available"
        assert result[0]["tags"] == {"Name": "my-gw"}
        assert result[0]["region"] == "ap-south-1"

    def test_handles_missing_optional_fields(self):
        gw = {
            "NatGatewayId": "nat-xyz",
            "State": "available",
            "Tags": [],
        }
        factory, _, _ = _make_client_factory(
            ec2_responses=[{"NatGateways": [gw]}]
        )
        collector = NATGatewayCollector(factory)
        result = collector.get_all_nat_gateways()
        assert result[0]["subnet_id"] is None
        assert result[0]["vpc_id"] is None
        assert result[0]["tags"] == {}


class TestGetNatGatewayMetrics:
    def test_returns_zero_when_no_datapoints(self):
        factory, _, cw = _make_client_factory()
        cw.get_metric_statistics.return_value = {"Datapoints": []}
        collector = NATGatewayCollector(factory)
        metrics = collector.get_nat_gateway_metrics("nat-abc")
        assert metrics["bytes_out_7d"] == 0.0
        assert metrics["bytes_in_7d"] == 0.0
        assert metrics["active_connections_avg"] == 0.0
        assert metrics["packets_out_7d"] == 0.0

    def test_sums_bytes_out_datapoints(self):
        factory, _, cw = _make_client_factory()

        def metric_side_effect(**kwargs):
            metric = kwargs["MetricName"]
            if metric == "BytesOutToDestination":
                return {"Datapoints": [{"Sum": 100.0}, {"Sum": 200.0}]}
            elif metric == "BytesInFromDestination":
                return {"Datapoints": [{"Sum": 50.0}]}
            elif metric == "PacketsOutToDestination":
                return {"Datapoints": [{"Sum": 1000.0}]}
            elif metric == "ActiveConnectionCount":
                return {"Datapoints": [{"Average": 5.0}, {"Average": 3.0}]}
            return {"Datapoints": []}

        cw.get_metric_statistics.side_effect = metric_side_effect
        collector = NATGatewayCollector(factory)
        metrics = collector.get_nat_gateway_metrics("nat-abc")

        assert metrics["bytes_out_7d"] == 300.0
        assert metrics["bytes_in_7d"] == 50.0
        assert metrics["packets_out_7d"] == 1000.0
        assert metrics["active_connections_avg"] == 4.0  # (5+3)/2

    def test_returns_zero_on_cloudwatch_exception(self):
        factory, _, cw = _make_client_factory()
        cw.get_metric_statistics.side_effect = Exception("CloudWatch error")
        collector = NATGatewayCollector(factory)
        metrics = collector.get_nat_gateway_metrics("nat-abc")
        assert metrics["bytes_out_7d"] == 0.0
        assert metrics["bytes_in_7d"] == 0.0
