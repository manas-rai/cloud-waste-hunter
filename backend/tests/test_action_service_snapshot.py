"""
Unit tests for ActionService snapshot-specific behaviour
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.action_service import ActionService, SafetyCheckFailedError


class TestLiveSnapshotSafetyCheck:
    def test_passes_when_no_ami_links(self):
        snapshot_client = MagicMock()
        snapshot_client.check_snapshot_ami_links.return_value = []

        service = ActionService()
        factory = MagicMock()

        with patch(
            "app.services.action_service.SnapshotClient",
            return_value=snapshot_client,
        ):
            # Should not raise
            service._live_snapshot_safety_check("snap-free", factory)

        snapshot_client.check_snapshot_ami_links.assert_called_once_with("snap-free")

    def test_raises_when_ami_links_exist(self):
        snapshot_client = MagicMock()
        snapshot_client.check_snapshot_ami_links.return_value = ["ami-111", "ami-222"]

        service = ActionService()
        factory = MagicMock()

        with patch(
            "app.services.action_service.SnapshotClient",
            return_value=snapshot_client,
        ):
            with pytest.raises(SafetyCheckFailedError) as exc_info:
                service._live_snapshot_safety_check("snap-linked", factory)

        assert "snap-linked" in str(exc_info.value)
        assert "ami-111" in str(exc_info.value)

    def test_error_message_lists_all_ami_ids(self):
        snapshot_client = MagicMock()
        snapshot_client.check_snapshot_ami_links.return_value = [
            "ami-aaa",
            "ami-bbb",
            "ami-ccc",
        ]

        service = ActionService()
        factory = MagicMock()

        with patch(
            "app.services.action_service.SnapshotClient",
            return_value=snapshot_client,
        ):
            with pytest.raises(SafetyCheckFailedError) as exc_info:
                service._live_snapshot_safety_check("snap-multi", factory)

        error_msg = str(exc_info.value)
        assert "ami-aaa" in error_msg
        assert "ami-bbb" in error_msg
        assert "ami-ccc" in error_msg


class TestSafetyCheckFailedErrorIsException:
    def test_is_exception_subclass(self):
        err = SafetyCheckFailedError("test error")
        assert isinstance(err, Exception)
        assert str(err) == "test error"
