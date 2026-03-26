"""
Snapshot Client - Thin wrapper around boto3 for snapshot-specific AWS calls
"""

from datetime import UTC, datetime

import structlog

from app.aws.client import AWSClientFactory

logger = structlog.get_logger()


class SnapshotNotFoundError(Exception):
    """Raised when a snapshot is not found in AWS"""


class SnapshotClient:
    """Thin wrapper for snapshot-specific EC2 API calls"""

    def __init__(self, client_factory: AWSClientFactory | None = None):
        if client_factory is None:
            client_factory = AWSClientFactory()
        self.ec2_client = client_factory.get_ec2_client()

    def describe_snapshot(self, snapshot_id: str) -> dict:
        """
        Get metadata about an EBS snapshot.

        Args:
            snapshot_id: EBS snapshot ID (e.g. snap-12345)

        Returns:
            dict with snapshot_id, size_gb, start_time, age_days, state

        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
        """
        try:
            response = self.ec2_client.describe_snapshots(SnapshotIds=[snapshot_id])
        except Exception as e:
            error_code = (
                getattr(e, "response", {}).get("Error", {}).get("Code", "")
            )
            if error_code == "InvalidSnapshot.NotFound":
                raise SnapshotNotFoundError(
                    f"Snapshot {snapshot_id} not found"
                ) from e
            raise

        snapshots = response.get("Snapshots", [])
        if not snapshots:
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")

        snap = snapshots[0]
        start_time = snap.get("StartTime")
        age_days = None
        if start_time:
            now = datetime.now(UTC)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=UTC)
            age_days = (now - start_time).days

        return {
            "snapshot_id": snap.get("SnapshotId"),
            "size_gb": snap.get("VolumeSize"),
            "start_time": start_time.isoformat() if start_time else None,
            "age_days": age_days,
            "state": snap.get("State"),
        }

    def check_snapshot_ami_links(self, snapshot_id: str) -> list[str]:
        """
        Check if any AMIs are backed by this snapshot.

        Args:
            snapshot_id: EBS snapshot ID

        Returns:
            List of AMI IDs in 'available' state that reference this snapshot

        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
        """
        # Verify snapshot exists first
        self.describe_snapshot(snapshot_id)

        try:
            response = self.ec2_client.describe_images(
                Filters=[
                    {
                        "Name": "block-device-mapping.snapshot-id",
                        "Values": [snapshot_id],
                    }
                ]
            )
        except Exception as e:
            logger.exception(
                "Failed to check AMI links for snapshot",
                snapshot_id=snapshot_id,
                error=str(e),
            )
            raise

        return [
            image["ImageId"]
            for image in response.get("Images", [])
            if image.get("State") == "available"
        ]


# Default instance
snapshot_client = SnapshotClient()
