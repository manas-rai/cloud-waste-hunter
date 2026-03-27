"""
Unit tests for DryRunExecutor snapshot preview
"""

import pytest

from app.safety.dry_run import DryRunExecutor


class TestPreviewSnapshotDelete:
    def test_returns_structured_result(self):
        executor = DryRunExecutor()
        result = executor.preview_snapshot_delete(
            "snap-abc123",
            {
                "estimated_monthly_savings_inr": 500.0,
                "size_gb": 50,
            },
        )

        assert result["action"] == "delete_ebs_snapshot"
        assert result["resource_id"] == "snap-abc123"
        assert result["resource_type"] == "ebs_snapshot"
        assert result["dry_run"] is True
        assert "impact" in result
        assert "risks" in result
        assert "recommendations" in result
        assert "previewed_at" in result

    def test_includes_snapshot_metadata_fields(self):
        executor = DryRunExecutor()
        result = executor.preview_snapshot_delete(
            "snap-abc",
            {
                "snapshot_age_days": 90,
                "snapshot_size_gb": 200.0,
                "linked_ami_ids": [],
            },
        )

        assert result["snapshot_age_days"] == 90
        assert result["snapshot_size_gb"] == 200.0
        assert result["linked_ami_id"] is None
        assert result["blocked_reason"] is None
        assert result["would_delete"] is True

    def test_sets_blocked_reason_when_ami_links_exist(self):
        executor = DryRunExecutor()
        result = executor.preview_snapshot_delete(
            "snap-linked",
            {
                "linked_ami_ids": ["ami-111", "ami-222"],
            },
        )

        assert result["linked_ami_id"] == "ami-111"
        assert result["linked_ami_ids"] == ["ami-111", "ami-222"]
        assert result["blocked_reason"] is not None
        assert "ami-111" in result["blocked_reason"]
        assert result["would_delete"] is False

    def test_no_blocked_reason_when_no_ami_links(self):
        executor = DryRunExecutor()
        result = executor.preview_snapshot_delete(
            "snap-free",
            {"linked_ami_ids": []},
        )

        assert result["blocked_reason"] is None
        assert result["linked_ami_id"] is None
        assert result["would_delete"] is True

    def test_size_gb_falls_back_to_size_gb_key(self):
        executor = DryRunExecutor()
        result = executor.preview_snapshot_delete(
            "snap-xyz",
            {"size_gb": 75},
        )

        assert result["snapshot_size_gb"] == 75

    def test_no_exception_when_snapshot_data_is_empty(self):
        executor = DryRunExecutor()
        # Should not raise even with an empty dict
        result = executor.preview_snapshot_delete("snap-empty", {})
        assert result["action"] == "delete_ebs_snapshot"
