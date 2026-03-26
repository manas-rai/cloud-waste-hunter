"""
Unit tests for backend/app/aws/snapshot_client.py
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.aws.snapshot_client import SnapshotClient, SnapshotNotFoundError


def _make_client(describe_snapshots_return=None, describe_images_return=None):
    """Helper: build a SnapshotClient backed by a mock boto3 EC2 client."""
    mock_ec2 = MagicMock()
    if describe_snapshots_return is not None:
        mock_ec2.describe_snapshots.return_value = describe_snapshots_return
    if describe_images_return is not None:
        mock_ec2.describe_images.return_value = describe_images_return

    mock_factory = MagicMock()
    mock_factory.get_ec2_client.return_value = mock_ec2

    client = SnapshotClient(client_factory=mock_factory)
    return client, mock_ec2


class TestDescribeSnapshot:
    def test_returns_correct_shape(self):
        start_time = datetime(2025, 1, 1, tzinfo=UTC)
        mock_response = {
            "Snapshots": [
                {
                    "SnapshotId": "snap-abc123",
                    "VolumeSize": 50,
                    "StartTime": start_time,
                    "State": "completed",
                }
            ]
        }
        client, mock_ec2 = _make_client(describe_snapshots_return=mock_response)

        result = client.describe_snapshot("snap-abc123")

        mock_ec2.describe_snapshots.assert_called_once_with(SnapshotIds=["snap-abc123"])
        assert result["snapshot_id"] == "snap-abc123"
        assert result["size_gb"] == 50
        assert result["state"] == "completed"
        assert result["age_days"] is not None
        assert result["age_days"] >= 0

    def test_raises_when_snapshot_not_found_empty_list(self):
        client, _ = _make_client(describe_snapshots_return={"Snapshots": []})

        with pytest.raises(SnapshotNotFoundError, match="snap-missing"):
            client.describe_snapshot("snap-missing")

    def test_raises_on_aws_not_found_error(self):
        mock_factory = MagicMock()
        mock_ec2 = MagicMock()
        err = Exception("Snapshot not found")
        err.response = {"Error": {"Code": "InvalidSnapshot.NotFound"}}
        mock_ec2.describe_snapshots.side_effect = err
        mock_factory.get_ec2_client.return_value = mock_ec2

        client = SnapshotClient(client_factory=mock_factory)

        with pytest.raises(SnapshotNotFoundError):
            client.describe_snapshot("snap-gone")

    def test_propagates_other_aws_errors(self):
        mock_factory = MagicMock()
        mock_ec2 = MagicMock()
        mock_ec2.describe_snapshots.side_effect = RuntimeError("Network error")
        mock_factory.get_ec2_client.return_value = mock_ec2

        client = SnapshotClient(client_factory=mock_factory)

        with pytest.raises(RuntimeError, match="Network error"):
            client.describe_snapshot("snap-xyz")

    def test_age_days_computed_correctly(self):
        days_ago = 30
        start_time = datetime.now(UTC) - timedelta(days=days_ago)
        mock_response = {
            "Snapshots": [
                {
                    "SnapshotId": "snap-age",
                    "VolumeSize": 10,
                    "StartTime": start_time,
                    "State": "completed",
                }
            ]
        }
        client, _ = _make_client(describe_snapshots_return=mock_response)
        result = client.describe_snapshot("snap-age")
        assert result["age_days"] == days_ago


class TestCheckSnapshotAmiLinks:
    def _snapshot_exists_response(self):
        return {
            "Snapshots": [
                {
                    "SnapshotId": "snap-linked",
                    "VolumeSize": 20,
                    "StartTime": datetime(2025, 6, 1, tzinfo=UTC),
                    "State": "completed",
                }
            ]
        }

    def test_returns_available_ami_ids(self):
        ami_response = {
            "Images": [
                {"ImageId": "ami-111", "State": "available"},
                {"ImageId": "ami-222", "State": "available"},
            ]
        }
        client, mock_ec2 = _make_client(
            describe_snapshots_return=self._snapshot_exists_response(),
            describe_images_return=ami_response,
        )

        result = client.check_snapshot_ami_links("snap-linked")

        mock_ec2.describe_images.assert_called_once_with(
            Filters=[
                {
                    "Name": "block-device-mapping.snapshot-id",
                    "Values": ["snap-linked"],
                }
            ]
        )
        assert result == ["ami-111", "ami-222"]

    def test_excludes_non_available_amis(self):
        ami_response = {
            "Images": [
                {"ImageId": "ami-111", "State": "available"},
                {"ImageId": "ami-deregistered", "State": "deregistered"},
            ]
        }
        client, _ = _make_client(
            describe_snapshots_return=self._snapshot_exists_response(),
            describe_images_return=ami_response,
        )

        result = client.check_snapshot_ami_links("snap-linked")

        assert result == ["ami-111"]

    def test_returns_empty_list_when_no_amis(self):
        client, _ = _make_client(
            describe_snapshots_return=self._snapshot_exists_response(),
            describe_images_return={"Images": []},
        )

        result = client.check_snapshot_ami_links("snap-linked")

        assert result == []

    def test_raises_snapshot_not_found(self):
        client, _ = _make_client(describe_snapshots_return={"Snapshots": []})

        with pytest.raises(SnapshotNotFoundError):
            client.check_snapshot_ami_links("snap-gone")
