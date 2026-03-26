"""
Unit tests for _live_snapshot_safety_check in action_service.py
"""

from unittest.mock import MagicMock, patch

import pytest

from app.aws.snapshot_client import SnapshotNotFoundError
from app.services.action_service import ActionService, SafetyCheckFailedError


def _service():
    return ActionService()


class TestLiveSnapshotSafetyCheck:
    def test_passes_when_no_ami_links(self):
        service = _service()
        mock_sc = MagicMock()
        mock_sc.check_snapshot_ami_links.return_value = []

        with patch("app.services.action_service.SnapshotClient", return_value=mock_sc):
            # Should not raise
            service._live_snapshot_safety_check("snap-clean")

        mock_sc.check_snapshot_ami_links.assert_called_once_with("snap-clean")

    def test_raises_safety_check_failed_when_ami_links_exist(self):
        service = _service()
        mock_sc = MagicMock()
        mock_sc.check_snapshot_ami_links.return_value = ["ami-111", "ami-222"]

        with patch("app.services.action_service.SnapshotClient", return_value=mock_sc):
            with pytest.raises(SafetyCheckFailedError) as exc_info:
                service._live_snapshot_safety_check("snap-linked")

        assert "ami-111" in str(exc_info.value)
        assert "ami-222" in str(exc_info.value)
        assert "snap-linked" in str(exc_info.value)

    def test_does_not_raise_when_snapshot_not_found(self):
        """If snapshot is already gone, treat as safe (nothing to delete)."""
        service = _service()
        mock_sc = MagicMock()
        mock_sc.check_snapshot_ami_links.side_effect = SnapshotNotFoundError(
            "snap-gone not found"
        )

        with patch("app.services.action_service.SnapshotClient", return_value=mock_sc):
            # Should NOT raise SafetyCheckFailedError
            service._live_snapshot_safety_check("snap-gone")

    def test_raises_single_ami_link(self):
        service = _service()
        mock_sc = MagicMock()
        mock_sc.check_snapshot_ami_links.return_value = ["ami-only"]

        with patch("app.services.action_service.SnapshotClient", return_value=mock_sc):
            with pytest.raises(SafetyCheckFailedError):
                service._live_snapshot_safety_check("snap-one-link")
