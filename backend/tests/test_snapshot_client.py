"""
Unit tests for SnapshotClient
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.aws.snapshot_client import SnapshotClient, SnapshotNotFoundError


def _make_client_factory(ec2_client):
    factory = MagicMock()
    factory.get_ec2_client.return_value = ec2_client
    return factory


class TestDescribeSnapshot:
    def test_returns_correct_shape(self):
        ec2 = MagicMock()
        start_time = datetime(2025, 1, 1, tzinfo=UTC)
        ec2.describe_snapshots.return_value = {
            "Snapshots": [
                {
                    "SnapshotId": "snap-abc123",
                    "VolumeSize": 50,
                    "StartTime": start_time,
                    "State": "completed",
                }
            ]
        }
        client = SnapshotClient(_make_client_factory(ec2))
        result = client.describe_snapshot("snap-abc123")

        ec2.describe_snapshots.assert_called_once_with(SnapshotIds=["snap-abc123"])
        assert result["snapshot_id"] == "snap-abc123"
        assert result["size_gb"] == 50
        assert result["state"] == "completed"
        assert result["age_days"] >= 0

    def test_age_days_computed_correctly(self):
        ec2 = MagicMock()
        # Snapshot created exactly 30 days ago
        start_time = datetime.now(UTC) - timedelta(days=30)
        ec2.describe_snapshots.return_value = {
            "Snapshots": [
                {
                    "SnapshotId": "snap-old",
                    "VolumeSize": 100,
                    "StartTime": start_time,
                    "State": "completed",
                }
            ]
        }
        client = SnapshotClient(_make_client_factory(ec2))
        result = client.describe_snapshot("snap-old")

        assert result["age_days"] == 30

    def test_raises_snapshot_not_found_on_client_error(self):
        ec2 = MagicMock()
        ec2.describe_snapshots.side_effect = ClientError(
            {"Error": {"Code": "InvalidSnapshot.NotFound", "Message": "not found"}},
            "DescribeSnapshots",
        )
        client = SnapshotClient(_make_client_factory(ec2))

        with pytest.raises(SnapshotNotFoundError):
            client.describe_snapshot("snap-missing")

    def test_raises_snapshot_not_found_when_empty_list(self):
        ec2 = MagicMock()
        ec2.describe_snapshots.return_value = {"Snapshots": []}
        client = SnapshotClient(_make_client_factory(ec2))

        with pytest.raises(SnapshotNotFoundError):
            client.describe_snapshot("snap-gone")

    def test_reraises_other_client_errors(self):
        ec2 = MagicMock()
        ec2.describe_snapshots.side_effect = ClientError(
            {"Error": {"Code": "UnauthorizedOperation", "Message": "no perms"}},
            "DescribeSnapshots",
        )
        client = SnapshotClient(_make_client_factory(ec2))

        with pytest.raises(ClientError):
            client.describe_snapshot("snap-abc")


class TestCheckSnapshotAmiLinks:
    def test_returns_active_ami_ids(self):
        ec2 = MagicMock()
        ec2.describe_images.return_value = {
            "Images": [
                {"ImageId": "ami-111", "State": "available"},
                {"ImageId": "ami-222", "State": "available"},
            ]
        }
        client = SnapshotClient(_make_client_factory(ec2))
        result = client.check_snapshot_ami_links("snap-abc")

        ec2.describe_images.assert_called_once_with(
            Filters=[
                {
                    "Name": "block-device-mapping.snapshot-id",
                    "Values": ["snap-abc"],
                }
            ]
        )
        assert result == ["ami-111", "ami-222"]

    def test_filters_out_non_available_amis(self):
        ec2 = MagicMock()
        ec2.describe_images.return_value = {
            "Images": [
                {"ImageId": "ami-available", "State": "available"},
                {"ImageId": "ami-deregistered", "State": "deregistered"},
                {"ImageId": "ami-pending", "State": "pending"},
            ]
        }
        client = SnapshotClient(_make_client_factory(ec2))
        result = client.check_snapshot_ami_links("snap-abc")

        assert result == ["ami-available"]

    def test_returns_empty_list_when_no_amis(self):
        ec2 = MagicMock()
        ec2.describe_images.return_value = {"Images": []}
        client = SnapshotClient(_make_client_factory(ec2))

        result = client.check_snapshot_ami_links("snap-orphan")
        assert result == []

    def test_returns_empty_list_on_error(self):
        ec2 = MagicMock()
        ec2.describe_images.side_effect = Exception("Network error")
        client = SnapshotClient(_make_client_factory(ec2))

        # Should not raise, returns empty list and logs warning
        result = client.check_snapshot_ami_links("snap-abc")
        assert result == []
