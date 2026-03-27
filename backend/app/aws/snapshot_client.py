"""
Snapshot-specific AWS client operations

Thin wrapper around boto3 for snapshot-related EC2 API calls.
"""

from datetime import UTC, datetime

import structlog
from botocore.exceptions import ClientError

from app.aws.client import AWSClientFactory

logger = structlog.get_logger()


class SnapshotNotFoundError(Exception):
    """Raised when a snapshot does not exist in AWS"""


class SnapshotClient:
    """Thin wrapper for snapshot-specific EC2 API calls"""

    def __init__(self, client_factory: AWSClientFactory):
        self.ec2_client = client_factory.get_ec2_client()

    def describe_snapshot(self, snapshot_id: str) -> dict:
        """
        Describe a snapshot and return its metadata.

        Args:
            snapshot_id: EBS snapshot ID

        Returns:
            dict with snapshot_id, size_gb, start_time, age_days, state

        Raises:
            SnapshotNotFoundError: if the snapshot no longer exists
        """
        try:
            response = self.ec2_client.describe_snapshots(SnapshotIds=[snapshot_id])
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("InvalidSnapshot.NotFound", "InvalidSnapshotID.NotFound"):
                raise SnapshotNotFoundError(
                    f"Snapshot {snapshot_id} not found"
                ) from e
            raise

        snapshots = response.get("Snapshots", [])
        if not snapshots:
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")

        snapshot = snapshots[0]
        start_time = snapshot["StartTime"]
        now = datetime.now(UTC)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        age_days = (now - start_time).days

        logger.info(
            "Described snapshot",
            snapshot_id=snapshot_id,
            age_days=age_days,
            size_gb=snapshot["VolumeSize"],
        )

        return {
            "snapshot_id": snapshot["SnapshotId"],
            "size_gb": snapshot["VolumeSize"],
            "start_time": start_time.isoformat(),
            "age_days": age_days,
            "state": snapshot["State"],
        }

    def check_snapshot_ami_links(self, snapshot_id: str) -> list[str]:
        """
        Return the IDs of any active AMIs that reference this snapshot.

        Uses the block-device-mapping.snapshot-id filter so only AMIs
        that directly use this snapshot are returned.

        Args:
            snapshot_id: EBS snapshot ID

        Returns:
            List of AMI IDs in 'available' state that reference this snapshot
        """
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
            logger.warning(
                "Error checking AMI links for snapshot",
                snapshot_id=snapshot_id,
                error=str(e),
            )
            return []

        ami_ids = [
            image["ImageId"]
            for image in response.get("Images", [])
            if image.get("State") == "available"
        ]

        if ami_ids:
            logger.warning(
                "Snapshot is linked to active AMIs",
                snapshot_id=snapshot_id,
                ami_ids=ami_ids,
            )

        return ami_ids
