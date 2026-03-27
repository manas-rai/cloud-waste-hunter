"""
Action Service - Orchestrates action approval and execution workflows
"""

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.aws.client import AWSClientFactory
from app.aws.snapshot_client import SnapshotClient
from app.repositories.audit_repository import audit_repository
from app.repositories.detection_repository import detection_repository
from app.safety.dry_run import DryRunExecutor
from app.safety.executor import SafeExecutor
from app.schemas.audit import ActionType, AuditLog, AuditStatus
from app.schemas.detection import Detection, DetectionStatus, ResourceType

logger = structlog.get_logger()


class SafetyCheckFailedError(Exception):
    """Raised when a pre-execution safety check fails (e.g. snapshot linked to active AMI)"""


class ActionService:
    """
    Service for action approval and execution

    Responsibilities:
    - Orchestrate action approval workflow
    - Execute actions via safety layer
    - Create audit trail
    - Handle dry-run vs actual execution
    """

    async def preview_action(
        self,
        db: AsyncSession,
        detection_id: int,
        client_factory: AWSClientFactory | None = None,
    ) -> dict:
        """
        Preview action impact (dry-run)

        Args:
            db: Database session
            detection_id: Detection ID
            client_factory: Optional AWS client factory (used to enrich snapshot previews)

        Returns:
            Preview result with impact analysis
        """
        # Get detection via repository
        detection = await detection_repository.find_by_id(db, detection_id)
        if not detection:
            raise ValueError(f"Detection {detection_id} not found")

        # Get dry-run executor
        dry_run = DryRunExecutor()
        detection_dict = detection.to_dict()

        # Preview based on resource type
        if detection.resource_type.value == "ec2_instance":
            preview = dry_run.preview_ec2_stop(detection.resource_id, detection_dict)
        elif detection.resource_type.value == "ebs_volume":
            preview = dry_run.preview_ebs_delete(detection.resource_id, detection_dict)
        elif detection.resource_type.value == "ebs_snapshot":
            # Enrich with live AWS snapshot metadata before preview
            if client_factory is None:
                client_factory = AWSClientFactory()
            snapshot_client = SnapshotClient(client_factory)
            try:
                snapshot_meta = snapshot_client.describe_snapshot(detection.resource_id)
                ami_links = snapshot_client.check_snapshot_ami_links(
                    detection.resource_id
                )
                detection_dict["snapshot_age_days"] = snapshot_meta["age_days"]
                detection_dict["snapshot_size_gb"] = snapshot_meta["size_gb"]
                detection_dict["linked_ami_ids"] = ami_links
            except Exception as e:
                logger.warning(
                    "Failed to get live snapshot metadata for preview",
                    detection_id=detection_id,
                    resource_id=detection.resource_id,
                    error=str(e),
                )
            preview = dry_run.preview_snapshot_delete(
                detection.resource_id, detection_dict
            )
        else:
            raise ValueError(f"Unknown resource type: {detection.resource_type.value}")

        return preview

    async def approve_and_execute(
        self,
        db: AsyncSession,
        detection_id: int,
        approved_by: str,
        dry_run: bool = False,
        client_factory: AWSClientFactory | None = None,
    ) -> dict:
        """
        Approve and execute action for a detection (TRANSACTIONAL)

        Ensures ACID properties:
        - ALL operations succeed together (detection + AWS action + audit log)
        - OR ALL operations are rolled back if any step fails

        Args:
            db: Database session
            detection_id: Detection ID
            approved_by: User who approved
            dry_run: If True, only simulate the action
            client_factory: Optional AWS client factory

        Returns:
            Execution result
        """
        # STEP 1: Get and validate detection
        detection = await detection_repository.find_by_id(db, detection_id)
        if not detection:
            raise ValueError(f"Detection {detection_id} not found")

        if detection.status != DetectionStatus.PENDING:
            raise ValueError(f"Detection already {detection.status.value}")

        # STEP 2: Update detection to APPROVED
        # SQLAlchemy tracks this change automatically
        detection.status = DetectionStatus.APPROVED
        detection.approved_by = approved_by
        detection.approved_at = datetime.now(UTC)

        # Initialize executor
        if client_factory is None:
            client_factory = AWSClientFactory()
        executor = SafeExecutor(client_factory)

        try:
            # STEP 3: Execute AWS action (external operation)
            action_result = await self._execute_action(
                executor,
                detection,
                approved_by,
                dry_run,
                client_factory,
            )

            # STEP 4: Update detection status based on AWS result
            # SQLAlchemy tracks these changes automatically
            if action_result.get("success") and not dry_run:
                detection.status = DetectionStatus.EXECUTED
            elif not action_result.get("success"):
                detection.status = DetectionStatus.FAILED

            # STEP 5: Create audit log
            # This object is added to the session automatically
            await self._create_audit_log(
                db,
                detection,
                action_result,
                approved_by,
                dry_run,
            )

            logger.info(
                "Action executed successfully",
                detection_id=detection_id,
                final_status=detection.status.value,
                success=action_result.get("success"),
            )

            # TRANSACTION COMMITS automatically in get_db() when function returns
            # All changes (detection + audit_log) committed together

        except Exception as e:
            # STEP 6: Handle AWS/execution failures
            # Record the failure but still commit the FAILED status
            logger.exception(
                "Action execution failed",
                detection_id=detection_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Mark detection as FAILED
            detection.status = DetectionStatus.FAILED

            # Create audit log for failed execution
            failed_audit_log = await self._create_failed_audit_log(
                db,
                detection,
                approved_by,
                str(e),
                dry_run,
            )

            # Return error response (commits the FAILED status + audit log)
            return {
                "detection": detection.model_dump(),
                "action_result": {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                "audit_log": failed_audit_log.model_dump(),
            }
        else:
            # TRANSACTION COMMITS automatically in get_db() when function returns
            # All changes (detection + audit_log) committed together
            return {"status": "success"}

    def _live_snapshot_safety_check(
        self,
        snapshot_id: str,
        client_factory: AWSClientFactory,
    ) -> None:
        """
        Verify the snapshot is not linked to any active AMIs before deletion.

        Args:
            snapshot_id: EBS snapshot ID to check
            client_factory: AWS client factory

        Raises:
            SafetyCheckFailedError: if the snapshot is still referenced by active AMIs
        """
        snapshot_client = SnapshotClient(client_factory)
        ami_ids = snapshot_client.check_snapshot_ami_links(snapshot_id)
        if ami_ids:
            raise SafetyCheckFailedError(
                f"Snapshot {snapshot_id} is still linked to active AMI(s): "
                f"{', '.join(ami_ids)}. Deregister the AMI(s) before deleting "
                "this snapshot."
            )

    async def _execute_action(
        self,
        executor: SafeExecutor,
        detection: Detection,
        approved_by: str,
        dry_run: bool,
        client_factory: AWSClientFactory | None = None,
    ) -> dict:
        """Execute action based on resource type"""
        resource_type = detection.resource_type.value
        resource_id = detection.resource_id

        if resource_type == "ec2_instance":
            return executor.stop_ec2_instance(resource_id, approved_by, dry_run)
        elif resource_type == "ebs_volume":
            return executor.delete_ebs_volume(resource_id, approved_by, dry_run)
        elif resource_type == "ebs_snapshot":
            # Run live safety check before actual deletion (not on dry runs)
            if not dry_run and client_factory is not None:
                self._live_snapshot_safety_check(resource_id, client_factory)
            return executor.delete_snapshot(resource_id, approved_by, dry_run)
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

    async def _create_audit_log(
        self,
        db: AsyncSession,
        detection: Detection,
        action_result: dict,
        approved_by: str,
        dry_run: bool,
    ) -> AuditLog:
        """Create audit log for action via repository"""
        # Map resource type to action type
        action_type_map = {
            ResourceType.EC2_INSTANCE.value: ActionType.STOP_EC2,
            ResourceType.EBS_VOLUME.value: ActionType.DELETE_EBS_VOLUME,
            ResourceType.EBS_SNAPSHOT.value: ActionType.DELETE_SNAPSHOT,
        }

        audit_log = AuditLog(
            detection_id=detection.id,
            action_type=action_type_map[detection.resource_type.value],
            resource_type=detection.resource_type.value,
            resource_id=detection.resource_id,
            status=(
                AuditStatus.SUCCESS
                if action_result.get("success")
                else AuditStatus.FAILED
            ),
            executed_by=approved_by,
            executed_at=datetime.now(UTC),
            dry_run=dry_run,
            result=action_result,
            error_message=action_result.get("error"),
            can_rollback=(
                detection.resource_type.value == ResourceType.EC2_INSTANCE.value
                and not dry_run
                and action_result.get("success")
            ),
            meta_data={},
        )

        return await audit_repository.create(db, audit_log)

    async def _create_failed_audit_log(
        self,
        db: AsyncSession,
        detection: Detection,
        approved_by: str,
        error_message: str,
        dry_run: bool = False,
    ) -> AuditLog:
        """Create audit log for failed action"""
        # Map resource type to action type
        action_type_map = {
            ResourceType.EC2_INSTANCE.value: ActionType.STOP_EC2,
            ResourceType.EBS_VOLUME.value: ActionType.DELETE_EBS_VOLUME,
            ResourceType.EBS_SNAPSHOT.value: ActionType.DELETE_SNAPSHOT,
        }

        audit_log = AuditLog(
            detection_id=detection.id,
            action_type=action_type_map[detection.resource_type.value],
            resource_type=detection.resource_type.value,
            resource_id=detection.resource_id,
            status=AuditStatus.FAILED,
            executed_by=approved_by,
            executed_at=datetime.now(UTC),
            dry_run=dry_run,
            result={"success": False},
            error_message=error_message,
            can_rollback=False,  # Failed actions cannot be rolled back
            meta_data={"failure_recorded": True},
        )

        return await audit_repository.create(db, audit_log)

    async def _create_rejection_audit_log(
        self,
        db: AsyncSession,
        detection: Detection,
        rejected_by: str,
    ) -> AuditLog:
        """
        Create audit log for rejection (when user decides NOT to execute action)

        This tracks the decision to NOT act on a detection, providing
        a complete audit trail of all user decisions.
        """
        # Map resource type to action type (what WOULD have been done)
        action_type_map = {
            ResourceType.EC2_INSTANCE.value: ActionType.STOP_EC2,
            ResourceType.EBS_VOLUME.value: ActionType.DELETE_EBS_VOLUME,
            ResourceType.EBS_SNAPSHOT.value: ActionType.DELETE_SNAPSHOT,
        }

        audit_log = AuditLog(
            detection_id=detection.id,
            action_type=action_type_map[detection.resource_type.value],
            resource_type=detection.resource_type.value,
            resource_id=detection.resource_id,
            status=AuditStatus.FAILED,  # Rejection is recorded as FAILED (action not taken)
            executed_by=rejected_by,
            executed_at=datetime.now(UTC),
            dry_run=False,
            result={
                "success": False,
                "rejected": True,
                "message": f"Detection rejected by {rejected_by}",
                "action": "rejection",
            },
            error_message=None,
            can_rollback=False,  # Rejections cannot be rolled back (no action was taken)
            meta_data={
                "rejection_reason": "User decided not to execute this action",
                "detection_confidence": detection.confidence_score,
                "estimated_savings": detection.estimated_monthly_savings_inr,
            },
        )

        return await audit_repository.create(db, audit_log)

    async def reject_detection(
        self,
        db: AsyncSession,
        detection_id: int,
        approved_by: str = "system",
    ) -> Detection:
        """
        Reject a detection (mark as not actionable)

        Args:
            db: Database session
            detection_id: Detection ID
            approved_by: User who rejected

        Returns:
            Updated detection
        """
        # Get detection
        detection = await detection_repository.find_by_id(db, detection_id)
        if not detection:
            raise ValueError(f"Detection {detection_id} not found")

        if detection.status != DetectionStatus.PENDING:
            raise ValueError(f"Detection already {detection.status.value}")

        # Update status to REJECTED
        # SQLAlchemy tracks this change automatically
        detection.status = DetectionStatus.REJECTED
        detection.approved_by = approved_by
        detection.approved_at = datetime.now(UTC)

        # Create audit log for rejection
        rejection_audit_log = await self._create_rejection_audit_log(
            db,
            detection,
            approved_by,
        )

        logger.info(
            "Detection rejected",
            detection_id=detection_id,
            approved_by=approved_by,
            audit_log_id=rejection_audit_log.id,
        )

        # TRANSACTION COMMITS automatically in get_db() when function returns
        # Both detection update and audit log are committed together
        return detection

    async def preview_batch_actions(
        self,
        db: AsyncSession,
        detection_ids: list[int],
    ) -> dict:
        """
        Preview batch actions

        Args:
            db: Database session
            detection_ids: List of detection IDs

        Returns:
            Batch preview results
        """
        detections = await detection_repository.find_by_ids(db, detection_ids)

        if len(detections) != len(detection_ids):
            raise ValueError("Some detections not found")

        dry_run = DryRunExecutor()
        detection_dicts = [d.to_dict() for d in detections]

        preview = dry_run.preview_batch_actions(detection_dicts)

        return preview


# Singleton instance
action_service = ActionService()
