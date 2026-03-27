"""
Tests for NAT Gateway collector, detector, and service.

Run with:
    cd backend
    uv run pytest tests/test_nat_gateway.py -v
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.aws.nat_gateway import NATGatewayCollector
from app.detection.nat_gateway_detector import NATGatewayDetector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BYTES_1GB = 1_073_741_824  # 1 GB threshold


def _make_gateway(nat_gateway_id: str = "nat-0abc123") -> dict:
    return {
        "nat_gateway_id": nat_gateway_id,
        "vpc_id": "vpc-0123456789abcdef0",
        "subnet_id": "subnet-0123456789abcdef0",
        "state": "available",
        "region": "us-east-1",
        "tags": {"Name": "test-nat"},
    }


def _make_metrics(
    nat_gateway_id: str,
    bytes_out_dest: float = 0.0,
    bytes_out_src: float = 0.0,
    avg_conn: float = 0.0,
) -> list[dict]:
    metrics = []
    ts = datetime.now(UTC)

    for metric_name, value in [
        ("BytesOutToDestination", bytes_out_dest),
        ("BytesOutToSource", bytes_out_src),
        ("ActiveConnectionCount", avg_conn),
    ]:
        metrics.append(
            {
                "nat_gateway_id": nat_gateway_id,
                "metric_name": metric_name,
                "timestamp": ts,
                "value": value,
                "unit": "Bytes" if "Bytes" in metric_name else "Count",
            }
        )

    return metrics


# ---------------------------------------------------------------------------
# Detector unit tests
# ---------------------------------------------------------------------------


class TestNATGatewayDetector:
    """Tests for NATGatewayDetector threshold logic."""

    def setup_method(self):
        # Use explicit thresholds so tests are independent of settings
        self.detector = NATGatewayDetector(
            bytes_threshold=BYTES_1GB, conn_threshold=1.0
        )

    def test_detector_flags_idle_gateway(self):
        """bytes=0, connections=0 → should be flagged as idle."""
        gw = _make_gateway("nat-idle")
        metrics = _make_metrics("nat-idle", bytes_out_dest=0, bytes_out_src=0, avg_conn=0)

        candidates = self.detector.detect([gw], {"nat-idle": metrics})

        assert len(candidates) == 1
        assert candidates[0]["resource_id"] == "nat-idle"
        assert candidates[0]["resource_type"] == "nat_gateway"
        assert candidates[0]["confidence_score"] == 0.95
        assert candidates[0]["estimated_monthly_cost_usd"] == 32.4

    def test_detector_ignores_active_gateway(self):
        """bytes=5 GB, connections=10 → should NOT be flagged."""
        gw = _make_gateway("nat-active")
        bytes_5gb = 5 * BYTES_1GB
        metrics = _make_metrics(
            "nat-active",
            bytes_out_dest=bytes_5gb / 2,
            bytes_out_src=bytes_5gb / 2,
            avg_conn=10,
        )

        candidates = self.detector.detect([gw], {"nat-active": metrics})

        assert len(candidates) == 0

    def test_detector_boundary_bytes_threshold(self):
        """bytes exactly at threshold (= 1 GB) → NOT flagged (< not <=)."""
        gw = _make_gateway("nat-boundary")
        metrics = _make_metrics(
            "nat-boundary",
            bytes_out_dest=BYTES_1GB,  # exactly at threshold
            bytes_out_src=0,
            avg_conn=0,
        )

        candidates = self.detector.detect([gw], {"nat-boundary": metrics})

        # total bytes = BYTES_1GB which is NOT < BYTES_1GB → not idle
        assert len(candidates) == 0

    def test_detector_flags_when_bytes_just_below_threshold(self):
        """bytes = threshold - 1 → flagged."""
        gw = _make_gateway("nat-below")
        metrics = _make_metrics(
            "nat-below",
            bytes_out_dest=BYTES_1GB - 1,
            bytes_out_src=0,
            avg_conn=0,
        )

        candidates = self.detector.detect([gw], {"nat-below": metrics})

        assert len(candidates) == 1

    def test_detector_active_connections_blocks_flag(self):
        """bytes=0, connections=1.0 (== threshold) → NOT flagged."""
        gw = _make_gateway("nat-conn")
        metrics = _make_metrics("nat-conn", bytes_out_dest=0, bytes_out_src=0, avg_conn=1.0)

        candidates = self.detector.detect([gw], {"nat-conn": metrics})

        # avg_conn = 1.0 is NOT < 1.0 → not idle
        assert len(candidates) == 0

    def test_detector_no_metrics_flags_as_idle(self):
        """No metrics at all → bytes=0, conn=0 → flagged."""
        gw = _make_gateway("nat-nometa")

        candidates = self.detector.detect([gw], {})

        assert len(candidates) == 1

    def test_detector_multiple_gateways(self):
        """Mixed active and idle gateways — only idle ones are returned."""
        gw_idle = _make_gateway("nat-idle-1")
        gw_active = _make_gateway("nat-active-1")

        metrics_idle = _make_metrics("nat-idle-1", bytes_out_dest=0, avg_conn=0)
        metrics_active = _make_metrics(
            "nat-active-1", bytes_out_dest=2 * BYTES_1GB, avg_conn=5
        )

        candidates = self.detector.detect(
            [gw_idle, gw_active],
            {"nat-idle-1": metrics_idle, "nat-active-1": metrics_active},
        )

        assert len(candidates) == 1
        assert candidates[0]["resource_id"] == "nat-idle-1"

    def test_detector_result_contains_required_fields(self):
        """Returned candidate dicts contain all expected fields."""
        gw = _make_gateway("nat-fields")
        metrics = _make_metrics("nat-fields")

        candidates = self.detector.detect([gw], {"nat-fields": metrics})

        assert len(candidates) == 1
        candidate = candidates[0]

        required_fields = {
            "resource_id",
            "resource_type",
            "resource_name",
            "region",
            "reason",
            "total_bytes_out_7d",
            "avg_active_connections",
            "confidence_score",
            "estimated_monthly_cost_usd",
            "detected_at",
            "metadata",
        }
        assert required_fields.issubset(candidate.keys())


# ---------------------------------------------------------------------------
# Collector unit tests (with mocked boto3)
# ---------------------------------------------------------------------------


class TestNATGatewayCollector:
    """Tests for NATGatewayCollector with mocked AWS clients."""

    def _make_factory(self, pages: list[list[dict]], metric_datapoints=None):
        """Build a mock AWSClientFactory with stubbed EC2 and CloudWatch."""
        ec2_mock = MagicMock()
        ec2_mock.meta.region_name = "us-east-1"

        # Paginator
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [
            {"NatGateways": page} for page in pages
        ]
        ec2_mock.get_paginator.return_value = paginator_mock

        cw_mock = MagicMock()
        cw_mock.get_metric_statistics.return_value = {
            "Datapoints": metric_datapoints or []
        }

        factory = MagicMock()
        factory.get_ec2_client.return_value = ec2_mock
        factory.get_cloudwatch_client.return_value = cw_mock
        return factory

    def test_list_nat_gateways_single_page(self):
        """Returns gateways from a single page."""
        pages = [
            [
                {
                    "NatGatewayId": "nat-abc",
                    "VpcId": "vpc-123",
                    "SubnetId": "subnet-456",
                    "State": "available",
                    "CreateTime": datetime.now(UTC),
                    "Tags": [{"Key": "Name", "Value": "prod-nat"}],
                }
            ]
        ]
        factory = self._make_factory(pages)
        collector = NATGatewayCollector(factory)

        gateways = collector.list_nat_gateways()

        assert len(gateways) == 1
        gw = gateways[0]
        assert gw["nat_gateway_id"] == "nat-abc"
        assert gw["vpc_id"] == "vpc-123"
        assert gw["subnet_id"] == "subnet-456"
        assert gw["state"] == "available"
        assert gw["region"] == "us-east-1"
        assert gw["tags"]["Name"] == "prod-nat"

    def test_collector_paginates_results(self):
        """Paginator returns multiple pages — all gateways are aggregated."""
        page1 = [
            {
                "NatGatewayId": "nat-page1-a",
                "VpcId": "vpc-1",
                "SubnetId": "sub-1",
                "State": "available",
                "CreateTime": datetime.now(UTC),
                "Tags": [],
            },
            {
                "NatGatewayId": "nat-page1-b",
                "VpcId": "vpc-2",
                "SubnetId": "sub-2",
                "State": "available",
                "CreateTime": datetime.now(UTC),
                "Tags": [],
            },
        ]
        page2 = [
            {
                "NatGatewayId": "nat-page2-a",
                "VpcId": "vpc-3",
                "SubnetId": "sub-3",
                "State": "available",
                "CreateTime": datetime.now(UTC),
                "Tags": [],
            }
        ]
        factory = self._make_factory([page1, page2])
        collector = NATGatewayCollector(factory)

        gateways = collector.list_nat_gateways()

        assert len(gateways) == 3
        ids = {g["nat_gateway_id"] for g in gateways}
        assert ids == {"nat-page1-a", "nat-page1-b", "nat-page2-a"}

    def test_get_nat_gateway_metrics_returns_all_metric_names(self):
        """Metrics are collected for all 5 expected metric names."""
        datapoints = [
            {"Timestamp": datetime.now(UTC), "Sum": 500.0, "Unit": "Bytes"},
        ]
        pages = [[]]  # empty gateway list — not needed for metrics test
        factory = self._make_factory(pages, metric_datapoints=datapoints)
        collector = NATGatewayCollector(factory)

        metrics = collector.get_nat_gateway_metrics("nat-abc", days=7)

        # 5 metrics × 1 datapoint each
        assert len(metrics) == 5
        metric_names = {m["metric_name"] for m in metrics}
        assert metric_names == {
            "BytesOutToDestination",
            "BytesOutToSource",
            "PacketsOutToDestination",
            "PacketsOutToSource",
            "ActiveConnectionCount",
        }

    def test_get_nat_gateway_metrics_handles_cloudwatch_error(self):
        """CloudWatch errors are swallowed; remaining metrics still returned."""
        factory = self._make_factory([[]])
        cw_mock = factory.get_cloudwatch_client.return_value

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("CloudWatch throttled")
            return {"Datapoints": []}

        cw_mock.get_metric_statistics.side_effect = side_effect
        collector = NATGatewayCollector(factory)

        # Should not raise; returns results for the remaining 4 metrics
        metrics = collector.get_nat_gateway_metrics("nat-err")
        assert isinstance(metrics, list)
        assert len(metrics) == 0  # remaining 4 calls return empty Datapoints


# ---------------------------------------------------------------------------
# Integration test: full service scan with mocked boto3
# ---------------------------------------------------------------------------


class TestNATGatewayServiceIntegration:
    """Integration test wiring collector → repository → detector via the service."""

    @pytest.mark.asyncio
    async def test_run_scan_returns_correct_structure(self):
        """run_scan() with mocked AWS and DB returns expected dict shape."""
        from app.services.nat_gateway_service import NATGatewayService

        # Mock factory
        ec2_mock = MagicMock()
        ec2_mock.meta.region_name = "us-east-1"
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [
            {
                "NatGateways": [
                    {
                        "NatGatewayId": "nat-svc-test",
                        "VpcId": "vpc-svc",
                        "SubnetId": "sub-svc",
                        "State": "available",
                        "CreateTime": datetime.now(UTC),
                        "Tags": [],
                    }
                ]
            }
        ]
        ec2_mock.get_paginator.return_value = paginator_mock

        cw_mock = MagicMock()
        cw_mock.get_metric_statistics.return_value = {"Datapoints": []}

        factory = MagicMock()
        factory.get_ec2_client.return_value = ec2_mock
        factory.get_cloudwatch_client.return_value = cw_mock

        # Mock DB session and repository
        db_mock = AsyncMock()

        with patch(
            "app.services.nat_gateway_service.nat_gateway_repository"
        ) as repo_mock:
            repo_mock.upsert = AsyncMock(return_value=MagicMock())
            repo_mock.bulk_insert_metrics = AsyncMock(return_value=0)

            service = NATGatewayService()
            result = await service.run_scan(
                db=db_mock, account_id="123456789012", client_factory=factory
            )

        assert "total_gateways" in result
        assert "total_idle_candidates" in result
        assert "candidates" in result
        assert result["total_gateways"] == 1
        # No metrics → idle → flagged as candidate
        assert result["total_idle_candidates"] == 1
        assert result["candidates"][0]["resource_id"] == "nat-svc-test"
