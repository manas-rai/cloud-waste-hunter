"""
Unit tests for snapshot preview in backend/app/safety/dry_run.py
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.safety.dry_run import DryRunExecutor


def _make_snapshot_client(age_days=90, size_gb=50, linked_amis=None):
    """Return a mock SnapshotClient with controlled responses."""
    if linked_amis is None:
        linked_amis = []

    mock_sc = MagicMock()
    mock_sc.describe_snapshot.return_value = {
        "snapshot_id": "snap-test",
        "size_gb": size_gb,
        "start_time": (datetime.now(UTC) - timedelta(days=age_days)).isoformat(),
        "age_days": age_days,
        "state": "completed",
    }
    mock_sc.check_snapshot_ami_links.return_value = linked_amis
    return mock_sc


def _make_client_factory(snapshot_client_mock):
    """Return a mock AWSClientFactory that will be injected into SnapshotClient."""
    mock_factory = MagicMock()
    return mock_factory


class TestPreviewSnapshotDelete:
    def test_returns_structured_dict(self):
        executor = DryRunExecutor()
        mock_sc = _make_snapshot_client()

        with patch("app.safety.dry_run.SnapshotClient", return_value=mock_sc):
            result = executor.preview_snapshot_delete("snap-test", {})

        assert result["action"] == "delete_ebs_snapshot"
        assert result["resource_id"] == "snap-test"
        assert result["resource_type"] == "ebs_snapshot"
        assert result["dry_run"] is True
        assert "impact" in result
        assert "risks" in result
        assert "recommendations" in result
        assert "previewed_at" in result

    def test_includes_live_snapshot_metadata(self):
        executor = DryRunExecutor()
        mock_sc = _make_snapshot_client(age_days=120, size_gb=200)

        with patch("app.safety.dry_run.SnapshotClient", return_value=mock_sc):
            result = executor.preview_snapshot_delete("snap-test", {})

        meta = result["snapshot_metadata"]
        assert meta["snapshot_age_days"] == 120
        assert meta["snapshot_size_gb"] == 200
        assert meta["linked_ami_ids"] == []

    def test_would_delete_true_when_no_ami_links(self):
        executor = DryRunExecutor()
        mock_sc = _make_snapshot_client(linked_amis=[])

        with patch("app.safety.dry_run.SnapshotClient", return_value=mock_sc):
            result = executor.preview_snapshot_delete("snap-test", {})

        assert result["would_delete"] is True
        assert result["blocked_reason"] is None

    def test_blocked_when_ami_links_exist(self):
        executor = DryRunExecutor()
        mock_sc = _make_snapshot_client(linked_amis=["ami-abc", "ami-def"])

        with patch("app.safety.dry_run.SnapshotClient", return_value=mock_sc):
            result = executor.preview_snapshot_delete("snap-test", {})

        assert result["would_delete"] is False
        assert "ami-abc" in result["blocked_reason"]
        assert "ami-def" in result["blocked_reason"]

    def test_still_returns_valid_dict_when_aws_unavailable(self):
        """Preview must not raise an exception if AWS calls fail."""
        executor = DryRunExecutor()

        mock_sc = MagicMock()
        mock_sc.describe_snapshot.side_effect = Exception("AWS unreachable")

        with patch("app.safety.dry_run.SnapshotClient", return_value=mock_sc):
            result = executor.preview_snapshot_delete(
                "snap-test",
                {"estimated_monthly_savings_inr": 500, "size_gb": 10},
            )

        # Must return a dict, not raise
        assert isinstance(result, dict)
        assert result["action"] == "delete_ebs_snapshot"

    def test_uses_snapshot_data_fallback_when_aws_unavailable(self):
        """When live call fails, falls back to values from snapshot_data arg."""
        executor = DryRunExecutor()
        mock_sc = MagicMock()
        mock_sc.describe_snapshot.side_effect = Exception("timeout")

        with patch("app.safety.dry_run.SnapshotClient", return_value=mock_sc):
            result = executor.preview_snapshot_delete(
                "snap-test",
                {"size_gb": 25, "age_days": 60, "estimated_monthly_savings_inr": 100},
            )

        # Falls back to passed-in values
        assert result["snapshot_metadata"]["snapshot_size_gb"] == 25
        assert result["snapshot_metadata"]["snapshot_age_days"] == 60
