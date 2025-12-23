"""
Dry-Run Preview System
Simulates actions without actually executing them
"""

from typing import List, Dict, Optional
from datetime import datetime
from app.core.config import settings


class DryRunExecutor:
    """Execute actions in dry-run mode to preview impact"""

    def __init__(self):
        self.dry_run_enabled = settings.DRY_RUN_ENABLED

    def preview_ec2_stop(self, instance_id: str, instance_data: Dict) -> Dict:
        """
        Preview stopping an EC2 instance

        Returns:
            Preview result with impact analysis
        """
        return {
            "action": "stop_ec2_instance",
            "resource_id": instance_id,
            "resource_type": "ec2_instance",
            "dry_run": True,
            "impact": {
                "instance_will_be": "stopped (can be restarted)",
                "data_preserved": True,
                "ip_address_changes": "Public IP will be released, Elastic IP preserved",
                "reversible": True,
                "estimated_savings_inr": instance_data.get(
                    "estimated_monthly_savings_inr", 0
                ),
            },
            "risks": [
                "Application downtime if instance is in use",
                "Any running processes will be terminated",
            ],
            "recommendations": [
                "Verify instance is truly idle",
                "Check for any scheduled tasks",
                "Ensure no critical services depend on this instance",
            ],
            "previewed_at": datetime.utcnow().isoformat(),
        }

    def preview_ebs_delete(self, volume_id: str, volume_data: Dict) -> Dict:
        """
        Preview deleting an EBS volume

        Returns:
            Preview result with impact analysis
        """
        return {
            "action": "delete_ebs_volume",
            "resource_id": volume_id,
            "resource_type": "ebs_volume",
            "dry_run": True,
            "impact": {
                "volume_will_be": "permanently deleted",
                "data_preserved": False,
                "reversible": False,  # Unless we have backup
                "estimated_savings_inr": volume_data.get(
                    "estimated_monthly_savings_inr", 0
                ),
                "size_gb": volume_data.get("size_gb", 0),
            },
            "risks": [
                "PERMANENT data loss - cannot be recovered",
                "Any snapshots will remain but volume data is gone",
            ],
            "recommendations": [
                "Create a snapshot before deletion if data might be needed",
                "Verify volume is truly unused",
                "Check for any recent access patterns",
            ],
            "previewed_at": datetime.utcnow().isoformat(),
        }

    def preview_snapshot_delete(self, snapshot_id: str, snapshot_data: Dict) -> Dict:
        """
        Preview deleting an EBS snapshot

        Returns:
            Preview result with impact analysis
        """
        return {
            "action": "delete_ebs_snapshot",
            "resource_id": snapshot_id,
            "resource_type": "ebs_snapshot",
            "dry_run": True,
            "impact": {
                "snapshot_will_be": "permanently deleted",
                "data_preserved": False,
                "reversible": False,
                "estimated_savings_inr": snapshot_data.get(
                    "estimated_monthly_savings_inr", 0
                ),
                "size_gb": snapshot_data.get("size_gb", 0),
            },
            "risks": [
                "PERMANENT data loss - snapshot cannot be recovered",
                "Cannot restore from this snapshot after deletion",
            ],
            "recommendations": [
                "Verify snapshot is not needed for disaster recovery",
                "Check if any AMIs depend on this snapshot",
                "Consider if snapshot might be needed for compliance",
            ],
            "previewed_at": datetime.utcnow().isoformat(),
        }

    def preview_batch_actions(self, detections: List[Dict]) -> Dict:
        """
        Preview a batch of actions

        Args:
            detections: List of detection results

        Returns:
            Batch preview with total impact
        """
        total_savings = sum(
            d.get("estimated_monthly_savings_inr", 0) for d in detections
        )
        action_counts = {}

        previews = []
        for detection in detections:
            resource_type = detection["resource_type"]
            resource_id = detection["resource_id"]

            action_counts[resource_type] = action_counts.get(resource_type, 0) + 1

            if resource_type == "ec2_instance":
                preview = self.preview_ec2_stop(resource_id, detection)
            elif resource_type == "ebs_volume":
                preview = self.preview_ebs_delete(resource_id, detection)
            elif resource_type == "ebs_snapshot":
                preview = self.preview_snapshot_delete(resource_id, detection)
            else:
                continue

            previews.append(preview)

        return {
            "batch_preview": True,
            "total_actions": len(previews),
            "action_breakdown": action_counts,
            "total_estimated_savings_inr": round(total_savings, 2),
            "previews": previews,
            "previewed_at": datetime.utcnow().isoformat(),
        }
