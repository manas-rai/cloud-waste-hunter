"""
AWS Resource Discovery and Data Collection
"""

from datetime import UTC, datetime, timedelta

import structlog

from app.aws.client import AWSClientFactory

logger = structlog.get_logger()


class EC2ResourceCollector:
    """Collect EC2 instance data"""

    def __init__(self, client_factory: AWSClientFactory):
        self.ec2_client = client_factory.get_ec2_client()
        self.cloudwatch = client_factory.get_cloudwatch_client()

    def get_all_instances(self) -> list[dict]:
        """
        Get all EC2 instances with their details

        Returns:
            List of instance dictionaries with metadata
        """
        instances = []
        paginator = self.ec2_client.get_paginator("describe_instances")

        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    instances.append(
                        {
                            "instance_id": instance["InstanceId"],
                            "instance_type": instance.get("InstanceType", "unknown"),
                            "state": instance["State"]["Name"],
                            "launch_time": instance["LaunchTime"],
                            "tags": {
                                tag["Key"]: tag["Value"]
                                for tag in instance.get("Tags", [])
                            },
                            "region": self.ec2_client.meta.region_name,
                            "vpc_id": instance.get("VpcId"),
                            "subnet_id": instance.get("SubnetId"),
                            "security_groups": [
                                sg["GroupId"]
                                for sg in instance.get("SecurityGroups", [])
                            ],
                        }
                    )

        return instances

    def get_instance_metrics(
        self, instance_id: str, days: int = 7, metric_name: str = "CPUUtilization"
    ) -> list[dict]:
        """
        Get CloudWatch metrics for an instance

        Args:
            instance_id: EC2 instance ID
            days: Number of days to look back
            metric_name: Metric to retrieve (CPUUtilization, NetworkIn, NetworkOut)

        Returns:
            List of metric data points
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=["Average", "Maximum", "Minimum"],
            )

            return sorted(response["Datapoints"], key=lambda x: x["Timestamp"])
        except Exception as e:
            # Log error but return empty list
            logger.warning(
                "Error fetching metrics", instance_id=instance_id, error=str(e)
            )
            return []


class EBSResourceCollector:
    """Collect EBS volume data"""

    def __init__(self, client_factory: AWSClientFactory):
        self.ec2_client = client_factory.get_ec2_client()

    def get_all_volumes(self) -> list[dict]:
        """
        Get all EBS volumes with their details

        Returns:
            List of volume dictionaries
        """
        volumes = []
        paginator = self.ec2_client.get_paginator("describe_volumes")

        for page in paginator.paginate():
            for volume in page["Volumes"]:
                volumes.append(
                    {
                        "volume_id": volume["VolumeId"],
                        "size_gb": volume["Size"],
                        "state": volume["State"],
                        "volume_type": volume["VolumeType"],
                        "create_time": volume["CreateTime"],
                        "attachments": volume.get("Attachments", []),
                        "tags": {
                            tag["Key"]: tag["Value"] for tag in volume.get("Tags", [])
                        },
                        "region": self.ec2_client.meta.region_name,
                        "encrypted": volume.get("Encrypted", False),
                    }
                )

        return volumes


class SnapshotCollector:
    """Collect EBS snapshot data"""

    def __init__(self, client_factory: AWSClientFactory):
        self.ec2_client = client_factory.get_ec2_client()

    def get_all_snapshots(self, owner_id: str | None = None) -> list[dict]:
        """
        Get all EBS snapshots

        Args:
            owner_id: AWS account ID (optional, defaults to self)

        Returns:
            List of snapshot dictionaries
        """
        snapshots = []
        paginator = self.ec2_client.get_paginator("describe_snapshots")

        filters = []
        if owner_id:
            filters.append({"Name": "owner-id", "Values": [owner_id]})
        else:
            # Get own snapshots
            filters.append({"Name": "owner-id", "Values": ["self"]})

        for page in paginator.paginate(Filters=filters):
            for snapshot in page["Snapshots"]:
                snapshots.append(
                    {
                        "snapshot_id": snapshot["SnapshotId"],
                        "volume_id": snapshot.get("VolumeId"),
                        "size_gb": snapshot["VolumeSize"],
                        "start_time": snapshot["StartTime"],
                        "state": snapshot["State"],
                        "description": snapshot.get("Description", ""),
                        "tags": {
                            tag["Key"]: tag["Value"] for tag in snapshot.get("Tags", [])
                        },
                        "region": self.ec2_client.meta.region_name,
                        "encrypted": snapshot.get("Encrypted", False),
                    }
                )

        return snapshots

    def get_associated_amis(self, snapshot_id: str) -> list[str]:
        """
        Check if snapshot is associated with any AMI

        Args:
            snapshot_id: Snapshot ID to check

        Returns:
            List of AMI IDs using this snapshot
        """
        amis = []
        try:
            # Get all AMIs
            response = self.ec2_client.describe_images(Owners=["self"])
            for image in response["Images"]:
                for block_device in image.get("BlockDeviceMappings", []):
                    if (
                        "Ebs" in block_device
                        and block_device["Ebs"].get("SnapshotId") == snapshot_id
                    ):
                        amis.append(image["ImageId"])
        except Exception as e:
            logger.warning(
                "Error checking AMIs for snapshot",
                snapshot_id=snapshot_id,
                error=str(e),
            )

        return amis
