"""
EBS Unattached Volume Detection
"""

from datetime import UTC, datetime

from structlog import get_logger

from app.aws.resources import EBSResourceCollector
from app.core.config import settings

logger = get_logger()


class EBSUnattachedDetector:
    """
    Detect unattached EBS volumes

    Criteria:
    - State = "available" (unattached)
    - No active attachments
    - Unattached for >= EBS_UNATTACHED_DAYS days (default: 30)
    """

    def __init__(self, resource_collector: EBSResourceCollector):
        self.collector = resource_collector
        self.min_days_unattached = settings.EBS_UNATTACHED_DAYS

    def detect_unattached_volumes(
        self, volumes: list[dict] | None = None
    ) -> list[dict]:
        """
        Detect unattached EBS volumes that have been unattached for >= 30 days

        Args:
            volumes: Optional list of volumes (if None, fetches all)

        Returns:
            List of unattached volume detections
        """
        try:
            if volumes is None:
                volumes = self.collector.get_all_volumes()

            detections = []

            for volume in volumes:
                # Check if volume is available (unattached)
                if volume["state"] != "available":
                    continue

                # Check if it has any attachments
                if volume.get("attachments") and len(volume["attachments"]) > 0:
                    continue  # Has attachments, skip

                # Parse creation time for age calculation
                create_time = volume["create_time"]
                if isinstance(create_time, str):
                    create_time = datetime.fromisoformat(
                        create_time.replace("Z", "+00:00")
                    )

                # Ensure create_time is timezone-aware (UTC) for subtraction
                if create_time.tzinfo is None:
                    create_time = create_time.replace(tzinfo=UTC)

                # Calculate days unattached
                days_unattached = (datetime.now(UTC) - create_time).days

                # Enforce minimum age threshold (default: 30 days)
                if days_unattached < self.min_days_unattached:
                    continue

                # Calculate estimated savings
                savings = self._estimate_savings(volume)

                create_time_iso = (
                    create_time.isoformat()
                    if isinstance(create_time, datetime)
                    else str(create_time)
                )

                detections.append(
                    {
                        "resource_type": "ebs_volume",
                        "resource_id": volume["volume_id"],
                        "resource_name": volume.get("tags", {}).get(
                            "Name", volume["volume_id"]
                        ),
                        "region": volume["region"],
                        "confidence_score": 0.95,  # High confidence for rule-based detection
                        "estimated_monthly_savings_inr": savings,
                        "detected_at": datetime.now(UTC).isoformat(),
                        "metadata": {
                            "size_gb": volume["size_gb"],
                            "volume_type": volume["volume_type"],
                            "availability_zone": volume.get("availability_zone", ""),
                            "days_unattached": days_unattached,
                            "create_time": create_time_iso,
                            "state": volume["state"],
                            "encrypted": volume.get("encrypted", False),
                            "tags": volume.get("tags", {}),
                        },
                    }
                )
        except Exception as e:
            logger.exception("Error detecting unattached volumes", error=str(e))
            raise

        return detections

    def _estimate_savings(self, volume: dict) -> float:
        """
        Estimate monthly savings in INR for deleting this volume

        EBS pricing varies by type and region
        """
        size_gb = volume["size_gb"]
        volume_type = volume.get("volume_type", "gp3")

        # Rough pricing in INR per GB-month (approximate)
        # gp3: ~₹0.10/GB-month, io1: ~₹0.15/GB-month, etc.
        pricing_map = {
            "gp2": 0.12,
            "gp3": 0.10,
            "io1": 0.15,
            "io2": 0.15,
            "st1": 0.05,
            "sc1": 0.03,
        }

        gb_month_rate = pricing_map.get(volume_type, 0.10)
        monthly_cost = size_gb * gb_month_rate

        return round(monthly_cost, 2)
