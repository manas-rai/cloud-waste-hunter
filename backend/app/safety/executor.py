"""
Safe Execution Layer
Executes actions with approval workflow and audit logging
"""

from typing import Dict, Optional
from datetime import datetime
from app.aws.client import AWSClientFactory
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class SafeExecutor:
    """Execute AWS actions safely with audit logging"""

    def __init__(self, client_factory: AWSClientFactory):
        self.client_factory = client_factory
        self.ec2_client = client_factory.get_ec2_client()

    def stop_ec2_instance(
        self, instance_id: str, approved_by: str, dry_run: bool = False
    ) -> Dict:
        """
        Stop an EC2 instance

        Args:
            instance_id: EC2 instance ID
            approved_by: User who approved the action
            dry_run: If True, only simulate the action

        Returns:
            Execution result
        """
        try:
            if dry_run:
                # Dry run - just verify permissions
                self.ec2_client.stop_instances(InstanceIds=[instance_id], DryRun=True)
                result = {
                    "success": True,
                    "action": "stop_ec2_instance",
                    "resource_id": instance_id,
                    "dry_run": True,
                    "message": "Dry run successful - would stop instance",
                }
            else:
                # Actual execution
                response = self.ec2_client.stop_instances(InstanceIds=[instance_id])

                current_state = response["StoppingInstances"][0]["CurrentState"]["Name"]
                previous_state = response["StoppingInstances"][0]["PreviousState"][
                    "Name"
                ]

                result = {
                    "success": True,
                    "action": "stop_ec2_instance",
                    "resource_id": instance_id,
                    "dry_run": False,
                    "previous_state": previous_state,
                    "current_state": current_state,
                    "approved_by": approved_by,
                    "executed_at": datetime.utcnow().isoformat(),
                    "message": f"Instance stopped successfully (was {previous_state})",
                }

            logger.info("EC2 stop executed", instance_id=instance_id, dry_run=dry_run)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error("EC2 stop failed", instance_id=instance_id, error=error_msg)

            return {
                "success": False,
                "action": "stop_ec2_instance",
                "resource_id": instance_id,
                "error": error_msg,
                "executed_at": datetime.utcnow().isoformat(),
            }

    def delete_ebs_volume(
        self, volume_id: str, approved_by: str, dry_run: bool = False
    ) -> Dict:
        """
        Delete an EBS volume

        Args:
            volume_id: EBS volume ID
            approved_by: User who approved the action
            dry_run: If True, only simulate the action

        Returns:
            Execution result
        """
        try:
            if dry_run:
                # Dry run - verify permissions
                self.ec2_client.delete_volume(VolumeId=volume_id, DryRun=True)
                result = {
                    "success": True,
                    "action": "delete_ebs_volume",
                    "resource_id": volume_id,
                    "dry_run": True,
                    "message": "Dry run successful - would delete volume",
                }
            else:
                # Actual execution
                self.ec2_client.delete_volume(VolumeId=volume_id)

                result = {
                    "success": True,
                    "action": "delete_ebs_volume",
                    "resource_id": volume_id,
                    "dry_run": False,
                    "approved_by": approved_by,
                    "executed_at": datetime.utcnow().isoformat(),
                    "message": "Volume deleted successfully",
                    "warning": "This action is PERMANENT and cannot be undone",
                }

            logger.info(
                "EBS volume delete executed", volume_id=volume_id, dry_run=dry_run
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "EBS volume delete failed", volume_id=volume_id, error=error_msg
            )

            return {
                "success": False,
                "action": "delete_ebs_volume",
                "resource_id": volume_id,
                "error": error_msg,
                "executed_at": datetime.utcnow().isoformat(),
            }

    def delete_snapshot(
        self, snapshot_id: str, approved_by: str, dry_run: bool = False
    ) -> Dict:
        """
        Delete an EBS snapshot

        Args:
            snapshot_id: EBS snapshot ID
            approved_by: User who approved the action
            dry_run: If True, only simulate the action

        Returns:
            Execution result
        """
        try:
            if dry_run:
                # Dry run - verify permissions
                self.ec2_client.delete_snapshot(SnapshotId=snapshot_id, DryRun=True)
                result = {
                    "success": True,
                    "action": "delete_ebs_snapshot",
                    "resource_id": snapshot_id,
                    "dry_run": True,
                    "message": "Dry run successful - would delete snapshot",
                }
            else:
                # Actual execution
                self.ec2_client.delete_snapshot(SnapshotId=snapshot_id)

                result = {
                    "success": True,
                    "action": "delete_ebs_snapshot",
                    "resource_id": snapshot_id,
                    "dry_run": False,
                    "approved_by": approved_by,
                    "executed_at": datetime.utcnow().isoformat(),
                    "message": "Snapshot deleted successfully",
                    "warning": "This action is PERMANENT and cannot be undone",
                }

            logger.info(
                "Snapshot delete executed", snapshot_id=snapshot_id, dry_run=dry_run
            )
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Snapshot delete failed", snapshot_id=snapshot_id, error=error_msg
            )

            return {
                "success": False,
                "action": "delete_ebs_snapshot",
                "resource_id": snapshot_id,
                "error": error_msg,
                "executed_at": datetime.utcnow().isoformat(),
            }
