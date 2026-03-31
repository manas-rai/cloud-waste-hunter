"""
Unit tests for EBSUnattachedDetector

Tests use mocked EBSResourceCollector — no real AWS calls are made.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.detection.ebs_detector import EBSUnattachedDetector


def _make_volume(
    volume_id: str = "vol-abc123",
    size_gb: int = 100,
    volume_type: str = "gp3",
    state: str = "available",
    days_ago: int = 45,
    attachments: list | None = None,
    availability_zone: str = "us-east-1a",
    region: str = "us-east-1",
    tags: dict | None = None,
    encrypted: bool = False,
) -> dict:
    """Helper to build a volume dict matching EBSResourceCollector output."""
    create_time = datetime.now(UTC) - timedelta(days=days_ago)
    return {
        "volume_id": volume_id,
        "size_gb": size_gb,
        "volume_type": volume_type,
        "state": state,
        "create_time": create_time,
        "availability_zone": availability_zone,
        "attachments": attachments or [],
        "region": region,
        "tags": tags or {},
        "encrypted": encrypted,
    }


@pytest.fixture()
def mock_collector():
    """Return a MagicMock standing in for EBSResourceCollector."""
    return MagicMock()


@pytest.fixture()
def detector(mock_collector):
    return EBSUnattachedDetector(resource_collector=mock_collector)


class TestDetectUnattachedVolumes:
    def test_returns_empty_list_when_no_volumes(self, detector, mock_collector):
        mock_collector.get_all_volumes.return_value = []
        result = detector.detect_unattached_volumes()
        assert result == []

    def test_excludes_volumes_younger_than_threshold(self, detector, mock_collector):
        """Volumes unattached for < 30 days must be excluded."""
        volume = _make_volume(days_ago=10)
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()
        assert result == []

    def test_excludes_volumes_exactly_at_threshold_minus_one(self, detector, mock_collector):
        """A volume unattached for 29 days should not appear."""
        volume = _make_volume(days_ago=29)
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()
        assert result == []

    def test_includes_volumes_at_threshold(self, detector, mock_collector):
        """A volume unattached for exactly 30 days must be included."""
        volume = _make_volume(days_ago=30)
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()
        assert len(result) == 1

    def test_includes_volumes_older_than_threshold(self, detector, mock_collector):
        """A volume unattached for > 30 days must be included."""
        volume = _make_volume(days_ago=90)
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()
        assert len(result) == 1

    def test_excludes_non_available_volumes(self, detector, mock_collector):
        """Volumes not in 'available' state must be excluded."""
        volume = _make_volume(state="in-use", days_ago=60)
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()
        assert result == []

    def test_excludes_volumes_with_attachments(self, detector, mock_collector):
        """Volumes that still have attachments must be excluded even if state=available."""
        volume = _make_volume(
            days_ago=60,
            attachments=[{"InstanceId": "i-abc", "State": "detaching"}],
        )
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()
        assert result == []

    def test_detection_fields(self, detector, mock_collector):
        """Returned detection must contain all required fields with correct values."""
        volume = _make_volume(
            volume_id="vol-test001",
            size_gb=50,
            volume_type="gp2",
            days_ago=45,
            availability_zone="eu-west-1b",
            region="eu-west-1",
        )
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()

        assert len(result) == 1
        det = result[0]

        assert det["resource_type"] == "ebs_volume"
        assert det["resource_id"] == "vol-test001"
        assert det["region"] == "eu-west-1"
        assert det["confidence_score"] == 0.95

        meta = det["metadata"]
        assert meta["size_gb"] == 50
        assert meta["volume_type"] == "gp2"
        assert meta["availability_zone"] == "eu-west-1b"
        assert meta["days_unattached"] == 45
        assert "create_time" in meta

    def test_days_unattached_is_correct(self, detector, mock_collector):
        """days_unattached in metadata must equal the number of days since creation."""
        volume = _make_volume(days_ago=60)
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()
        assert result[0]["metadata"]["days_unattached"] == 60

    def test_string_create_time_is_parsed(self, detector, mock_collector):
        """If create_time is a string it should still be parsed and filtered correctly."""
        create_time_str = (datetime.now(UTC) - timedelta(days=40)).isoformat()
        volume = _make_volume(days_ago=40)
        volume["create_time"] = create_time_str
        mock_collector.get_all_volumes.return_value = [volume]
        result = detector.detect_unattached_volumes()
        assert len(result) == 1
        assert result[0]["metadata"]["days_unattached"] == 40

    def test_accepts_injected_volumes(self, detector, mock_collector):
        """When volumes list is passed directly, the collector is not called."""
        volumes = [_make_volume(days_ago=35)]
        result = detector.detect_unattached_volumes(volumes=volumes)
        mock_collector.get_all_volumes.assert_not_called()
        assert len(result) == 1


class TestEstimateSavings:
    """Tests for the per-volume-type pricing map."""

    @pytest.mark.parametrize(
        "volume_type, size_gb, expected_savings",
        [
            ("gp2", 100, 12.0),
            ("gp3", 100, 10.0),
            ("io1", 100, 15.0),
            ("io2", 100, 15.0),
            ("st1", 100, 5.0),
            ("sc1", 100, 3.0),
            ("unknown_type", 100, 10.0),  # falls back to default 0.10
        ],
    )
    def test_savings_by_volume_type(
        self, detector, volume_type, size_gb, expected_savings
    ):
        volume = {"size_gb": size_gb, "volume_type": volume_type}
        assert detector._estimate_savings(volume) == expected_savings

    def test_savings_rounded_to_two_decimals(self, detector):
        volume = {"size_gb": 3, "volume_type": "gp3"}
        savings = detector._estimate_savings(volume)
        assert savings == round(savings, 2)


class TestCustomThreshold:
    def test_custom_threshold_respected(self, mock_collector):
        """Overriding min_days_unattached on the detector object should work."""
        with patch("app.detection.ebs_detector.settings") as mock_settings:
            mock_settings.EBS_UNATTACHED_DAYS = 60
            detector = EBSUnattachedDetector(resource_collector=mock_collector)

        # Volume unattached 45 days — below custom threshold of 60
        volume = _make_volume(days_ago=45)
        result = detector.detect_unattached_volumes(volumes=[volume])
        assert result == []

        # Volume unattached 65 days — above custom threshold of 60
        volume2 = _make_volume(volume_id="vol-old", days_ago=65)
        result2 = detector.detect_unattached_volumes(volumes=[volume2])
        assert len(result2) == 1
