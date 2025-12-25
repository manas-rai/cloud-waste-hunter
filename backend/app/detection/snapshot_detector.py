"""
EBS Snapshot Detection (Old Snapshots)
"""

from datetime import UTC, datetime, timedelta

from app.aws.resources import SnapshotCollector
from app.core.config import settings


class SnapshotDetector:
    """
    Detect old snapshots that can be deleted

    Criteria:
    - Age > 90 days
    - No associated AMI
    - Confidence scoring based on retention patterns
    """

    def __init__(self, resource_collector: SnapshotCollector):
        self.collector = resource_collector
        self.snapshot_age_days = settings.SNAPSHOT_AGE_DAYS

    def detect_old_snapshots(self, snapshots: list[dict] | None = None) -> list[dict]:
        """
        Detect old snapshots without associated AMIs

        Args:
            snapshots: Optional list of snapshots (if None, fetches all)

        Returns:
            List of old snapshot detections with confidence scores
        """
        if snapshots is None:
            snapshots = self.collector.get_all_snapshots()

        detections = []
        cutoff_date = datetime.now(UTC) - timedelta(days=self.snapshot_age_days)

        for snapshot in snapshots:
            # Skip if not completed
            if snapshot["state"] != "completed":
                continue

            # Check age
            start_time = snapshot["start_time"]
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

            if start_time > cutoff_date:
                continue  # Too recent

            # Check if associated with AMI
            associated_amis = self.collector.get_associated_amis(
                snapshot["snapshot_id"]
            )
            if associated_amis:
                continue  # Has associated AMI, skip

            # Calculate age
            age_days = (datetime.now(UTC) - start_time.replace(tzinfo=None)).days

            # Calculate confidence score based on retention patterns
            confidence = self._calculate_confidence(snapshot, age_days)

            # Calculate estimated savings
            savings = self._estimate_savings(snapshot)

            detections.append(
                {
                    "resource_type": "ebs_snapshot",
                    "resource_id": snapshot["snapshot_id"],
                    "resource_name": snapshot.get("tags", {}).get(
                        "Name", snapshot["snapshot_id"]
                    ),
                    "region": snapshot["region"],
                    "size_gb": snapshot["size_gb"],
                    "age_days": age_days,
                    "start_time": (
                        start_time.isoformat()
                        if isinstance(start_time, datetime)
                        else str(start_time)
                    ),
                    "confidence_score": confidence,
                    "estimated_monthly_savings_inr": savings,
                    "detected_at": datetime.now(UTC).isoformat(),
                    "metadata": {
                        "volume_id": snapshot.get("volume_id"),
                        "description": snapshot.get("description", ""),
                        "encrypted": snapshot.get("encrypted", False),
                        "tags": snapshot.get("tags", {}),
                        "associated_amis": associated_amis,  # Empty but included for clarity
                    },
                }
            )

        return detections

    def _calculate_confidence(self, snapshot: dict, age_days: int) -> float:
        """
        Calculate confidence score for deletion

        Higher confidence for:
        - Older snapshots
        - No description or generic description
        - No special tags
        - No associated volume
        """
        confidence = 0.7  # Base confidence

        # Age factor (older = higher confidence)
        if age_days > 180:
            confidence += 0.15
        elif age_days > 365:
            confidence += 0.2

        # Description factor
        description = snapshot.get("description", "").lower()
        if not description or "backup" in description or "snapshot" in description:
            confidence += 0.05  # Generic description

        # Tags factor
        tags = snapshot.get("tags", {})
        if not tags or "backup" not in str(tags).lower():
            confidence += 0.05

        # Volume existence factor
        if not snapshot.get("volume_id"):
            confidence += 0.05  # Original volume may be deleted

        return min(confidence, 0.95)  # Cap at 0.95

    def _estimate_savings(self, snapshot: dict) -> float:
        """
        Estimate monthly savings in INR for deleting this snapshot

        EBS snapshot pricing: ~₹0.05/GB-month (approximate)
        """
        size_gb = snapshot["size_gb"]
        gb_month_rate = 0.05  # ₹0.05 per GB-month
        monthly_cost = size_gb * gb_month_rate

        return round(monthly_cost, 2)
