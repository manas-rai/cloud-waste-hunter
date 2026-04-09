"""
Unit tests for NatGatewayDetector
"""

from unittest.mock import MagicMock, patch

import pytest

from app.detection.nat_gateway_detector import NatGatewayDetector

THRESHOLD = 1_000_000_000  # 1 GB


def _make_ngw(nat_gw_id="nat-0abc1234", region="us-east-1"):
    return {
        "id": nat_gw_id,
        "name": nat_gw_id,
        "vpc_id": "vpc-0abc1234",
        "subnet_id": "subnet-0abc1234",
        "state": "available",
        "account_id": None,
        "region": region,
    }


def _mock_cw_client(bytes_in: float, bytes_out: float):
    """Build a CloudWatch mock that returns given byte totals."""
    cw = MagicMock()

    def _get_metric_statistics(**kwargs):
        metric = kwargs["MetricName"]
        if metric == "BytesInFromSource":
            value = bytes_in
        else:
            value = bytes_out
        return {
            "Datapoints": [{"Sum": value, "Timestamp": "2025-01-01T00:00:00Z"}]
        }

    cw.get_metric_statistics.side_effect = _get_metric_statistics
    return cw


class TestNatGatewayDetector:
    def setup_method(self):
        self.detector = NatGatewayDetector(
            threshold_bytes=THRESHOLD, lookback_days=7
        )

    def test_detect_idle_gateway(self):
        """Total bytes below threshold → is_idle=True"""
        ngw = _make_ngw()
        cw = _mock_cw_client(bytes_in=200_000_000, bytes_out=100_000_000)

        results = self.detector.detect([ngw], cw_client=cw)

        assert len(results) == 1
        detection = results[0]
        assert detection.resource_id == "nat-0abc1234"
        assert detection.is_idle is True
        assert detection.total_bytes_7d == pytest.approx(300_000_000)
        assert detection.bytes_in_7d == pytest.approx(200_000_000)
        assert detection.bytes_out_7d == pytest.approx(100_000_000)
        assert 0.0 < detection.waste_score <= 1.0

    def test_detect_active_gateway(self):
        """Total bytes above threshold → is_idle=False"""
        ngw = _make_ngw()
        cw = _mock_cw_client(bytes_in=800_000_000, bytes_out=500_000_000)

        results = self.detector.detect([ngw], cw_client=cw)

        assert len(results) == 1
        detection = results[0]
        assert detection.is_idle is False
        assert detection.total_bytes_7d == pytest.approx(1_300_000_000)
        assert detection.waste_score == pytest.approx(0.0)

    def test_detect_missing_metrics(self):
        """Empty CloudWatch response → treated as idle (0 bytes)"""
        ngw = _make_ngw()
        cw = MagicMock()
        cw.get_metric_statistics.return_value = {"Datapoints": []}

        results = self.detector.detect([ngw], cw_client=cw)

        assert len(results) == 1
        detection = results[0]
        assert detection.is_idle is True
        assert detection.total_bytes_7d == pytest.approx(0.0)
        assert detection.waste_score == pytest.approx(1.0)

    def test_detect_no_gateways(self):
        """Empty gateway list returns empty detections"""
        cw = MagicMock()
        results = self.detector.detect([], cw_client=cw)
        assert results == []

    def test_detect_exact_threshold_is_not_idle(self):
        """Total bytes exactly at threshold → is_idle=False"""
        ngw = _make_ngw()
        cw = _mock_cw_client(bytes_in=500_000_000, bytes_out=500_000_000)

        results = self.detector.detect([ngw], cw_client=cw)

        assert len(results) == 1
        assert results[0].is_idle is False
        assert results[0].waste_score == pytest.approx(0.0)

    def test_detect_just_below_threshold_is_idle(self):
        """Total bytes just below threshold → is_idle=True"""
        ngw = _make_ngw()
        cw = _mock_cw_client(bytes_in=499_999_999, bytes_out=499_999_999)

        results = self.detector.detect([ngw], cw_client=cw)

        assert len(results) == 1
        assert results[0].is_idle is True

    def test_detect_cloudwatch_error_treated_as_idle(self):
        """CloudWatch exception → metric defaults to 0 → treated as idle"""
        ngw = _make_ngw()
        cw = MagicMock()
        cw.get_metric_statistics.side_effect = Exception("CloudWatch unavailable")

        results = self.detector.detect([ngw], cw_client=cw)

        assert len(results) == 1
        assert results[0].is_idle is True
        assert results[0].total_bytes_7d == pytest.approx(0.0)

    def test_metadata_fields_populated(self):
        """VPC and subnet fields are propagated to the detection model"""
        ngw = _make_ngw()
        ngw["vpc_id"] = "vpc-test"
        ngw["subnet_id"] = "subnet-test"
        cw = _mock_cw_client(0, 0)

        results = self.detector.detect([ngw], cw_client=cw)

        assert results[0].vpc_id == "vpc-test"
        assert results[0].subnet_id == "subnet-test"
        assert results[0].region == "us-east-1"
