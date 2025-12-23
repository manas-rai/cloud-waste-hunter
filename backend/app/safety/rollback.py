"""
Rollback Mechanism for Executed Actions
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from app.aws.client import AWSClientFactory
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class RollbackExecutor:
    """Execute rollbacks for previously executed actions"""

    def __init__(self, client_factory: AWSClientFactory):
        self.client_factory = client_factory
        self.ec2_client = client_factory.get_ec2_client()
        self.retention_days = settings.ROLLBACK_RETENTION_DAYS

    def can_rollback(self, audit_log: Dict) -> bool:
        """
        Check if an action can be rolled back

        Args:
            audit_log: Audit log entry

        Returns:
            True if rollback is possible
        """
        # Only EC2 stop actions can be rolled back (by starting the instance)
        if audit_log.get("action_type") != "stop_ec2_instance":
            return False

        # Check if already rolled back
        if audit_log.get("rolled_back_at"):
            return False

        # Check if within retention period
        executed_at = audit_log.get("executed_at")
        if isinstance(executed_at, str):
            executed_at = datetime.fromisoformat(executed_at.replace("Z", "+00:00"))

        if executed_at:
            age = datetime.utcnow() - executed_at.replace(tzinfo=None)
            if age.days > self.retention_days:
                return False

        # Check if action was successful
        if audit_log.get("status") != "success":
            return False

        # Check if it was a dry run
        if audit_log.get("dry_run"):
            return False

        return True

    def rollback_ec2_stop(self, instance_id: str, rolled_back_by: str) -> Dict:
        """
        Rollback EC2 stop action by starting the instance

        Args:
            instance_id: EC2 instance ID
            rolled_back_by: User performing rollback

        Returns:
            Rollback result
        """
        try:
            # Start the instance
            response = self.ec2_client.start_instances(InstanceIds=[instance_id])

            current_state = response["StartingInstances"][0]["CurrentState"]["Name"]
            previous_state = response["StartingInstances"][0]["PreviousState"]["Name"]

            result = {
                "success": True,
                "action": "rollback_ec2_stop",
                "resource_id": instance_id,
                "previous_state": previous_state,
                "current_state": current_state,
                "rolled_back_by": rolled_back_by,
                "rolled_back_at": datetime.utcnow().isoformat(),
                "message": f"Instance started successfully (was {previous_state})",
            }

            logger.info("EC2 rollback executed", instance_id=instance_id)
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "EC2 rollback failed", instance_id=instance_id, error=error_msg
            )

            return {
                "success": False,
                "action": "rollback_ec2_stop",
                "resource_id": instance_id,
                "error": error_msg,
                "rolled_back_at": datetime.utcnow().isoformat(),
            }

    def rollback_action(self, audit_log: Dict, rolled_back_by: str) -> Dict:
        """
        Rollback an action based on audit log

        Args:
            audit_log: Audit log entry
            rolled_back_by: User performing rollback

        Returns:
            Rollback result
        """
        if not self.can_rollback(audit_log):
            return {
                "success": False,
                "error": "Action cannot be rolled back",
                "reason": "Either outside retention period, already rolled back, or not a rollbackable action type",
            }

        action_type = audit_log.get("action_type")
        resource_id = audit_log.get("resource_id")

        if action_type == "stop_ec2_instance":
            return self.rollback_ec2_stop(resource_id, rolled_back_by)
        else:
            return {
                "success": False,
                "error": f"Rollback not supported for action type: {action_type}",
            }
