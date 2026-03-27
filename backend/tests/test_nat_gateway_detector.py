"""
Unit tests for NatGatewayDetector
"""

import pytest

from app.detection.nat_gateway_detector import IDLE_THRESHOLD_BYTES, NatGatewayDetector


@pytest.fixture
def detector():
    return NatGatewayDetector()


def _make_gateway(
    nat_gateway_id: str = "nat-0123456789abcdef0",
    bytes_out: float = 0.0,
    bytes_in: float = 0.0,
    region: str = "ap-south-1",
    vpc_id: str = "vpc-abc",
    subnet_id: str = "subnet-def",
    tags: dict | None = None,
) -> dict:
    return {
        "nat_gateway_id": nat_gateway_id,
        "bytes_out_7d": bytes_out,
        "bytes_in_7d": bytes_in,
        "active_connections_avg": 0.0,
        "packets_out_7d": 0.0,
        "region": region,
        "vpc_id": vpc_id,
        "subnet_id": subnet_id,
        "tags": tags or {},
    }


class TestNatGatewayDetectorDetect:
    def test_zero_traffic_gateway_is_flagged(self, detector):
        gw = _make_gateway(bytes_out=0.0, bytes_in=0.0)
        results = detector.detect([gw])
        assert len(results) == 1
        assert results[0]["resource_type"] == "nat_gateway"
        assert results[0]["resource_id"] == gw["nat_gateway_id"]
        assert results[0]["confidence_score"] == 1.0

    def test_idle_gateway_below_threshold_is_flagged(self, detector):
        # 500 MB total — below 1 GB threshold
        half_gb = 500 * 1024 * 1024
        gw = _make_gateway(bytes_out=half_gb / 2, bytes_in=half_gb / 2)
        results = detector.detect([gw])
        assert len(results) == 1
        assert results[0]["confidence_score"] > 0.0
        assert results[0]["confidence_score"] < 1.0

    def test_active_gateway_above_threshold_is_not_flagged(self, detector):
        # 2 GB total — above 1 GB threshold
        two_gb = 2 * IDLE_THRESHOLD_BYTES
        gw = _make_gateway(bytes_out=two_gb / 2, bytes_in=two_gb / 2)
        results = detector.detect([gw])
        assert len(results) == 0

    def test_gateway_exactly_at_threshold_is_not_flagged(self, detector):
        # Exactly 1 GB — not idle (requires < threshold)
        gw = _make_gateway(
            bytes_out=IDLE_THRESHOLD_BYTES / 2,
            bytes_in=IDLE_THRESHOLD_BYTES / 2,
        )
        results = detector.detect([gw])
        assert len(results) == 0

    def test_gateway_with_missing_metrics_is_treated_as_idle(self, detector):
        # Missing bytes fields — defaults to 0, so it is flagged
        gw = {
            "nat_gateway_id": "nat-missing",
            "region": "us-east-1",
            "vpc_id": "vpc-x",
            "subnet_id": "subnet-y",
            "tags": {},
        }
        results = detector.detect([gw])
        assert len(results) == 1
        assert results[0]["confidence_score"] == 1.0

    def test_gateway_with_none_metrics_is_treated_as_idle(self, detector):
        gw = _make_gateway(bytes_out=None, bytes_in=None)
        results = detector.detect([gw])
        assert len(results) == 1

    def test_confidence_proportional_to_traffic(self, detector):
        quarter_gb = IDLE_THRESHOLD_BYTES // 4
        gw = _make_gateway(bytes_out=quarter_gb, bytes_in=0)
        results = detector.detect([gw])
        assert len(results) == 1
        # 25% of threshold → confidence ≈ 0.75
        assert abs(results[0]["confidence_score"] - 0.75) < 0.01

    def test_detection_resource_type_is_nat_gateway(self, detector):
        gw = _make_gateway()
        results = detector.detect([gw])
        assert results[0]["resource_type"] == "nat_gateway"

    def test_detection_uses_name_tag_as_resource_name(self, detector):
        gw = _make_gateway(tags={"Name": "my-nat-gw"})
        results = detector.detect([gw])
        assert results[0]["resource_name"] == "my-nat-gw"

    def test_detection_falls_back_to_id_when_no_name_tag(self, detector):
        gw = _make_gateway(nat_gateway_id="nat-abc", tags={})
        results = detector.detect([gw])
        assert results[0]["resource_name"] == "nat-abc"

    def test_metadata_contains_waste_reason(self, detector):
        gw = _make_gateway()
        results = detector.detect([gw])
        assert "waste_reason" in results[0]["metadata"]
        assert "1 GB" in results[0]["metadata"]["waste_reason"]

    def test_empty_input_returns_empty_list(self, detector):
        assert detector.detect([]) == []

    def test_multiple_gateways_mixed(self, detector):
        idle_gw = _make_gateway(nat_gateway_id="nat-idle", bytes_out=0, bytes_in=0)
        active_gw = _make_gateway(
            nat_gateway_id="nat-active",
            bytes_out=IDLE_THRESHOLD_BYTES,
            bytes_in=IDLE_THRESHOLD_BYTES,
        )
        results = detector.detect([idle_gw, active_gw])
        assert len(results) == 1
        assert results[0]["resource_id"] == "nat-idle"

    def test_estimated_savings_is_positive(self, detector):
        gw = _make_gateway()
        results = detector.detect([gw])
        assert results[0]["estimated_monthly_savings_inr"] > 0

    def test_detection_includes_region(self, detector):
        gw = _make_gateway(region="eu-west-1")
        results = detector.detect([gw])
        assert results[0]["region"] == "eu-west-1"
