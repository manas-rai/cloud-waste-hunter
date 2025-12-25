"""
Detection Service - Orchestrates detection workflows
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.aws.client import AWSClientFactory
from app.aws.resources import (
    EBSResourceCollector,
    EC2ResourceCollector,
    SnapshotCollector,
)
from app.detection.ebs_detector import EBSUnattachedDetector
from app.detection.ec2_detector import EC2IdleDetector
from app.detection.snapshot_detector import SnapshotDetector
from app.repositories.detection_repository import detection_repository
from app.schemas.detection import ResourceType

logger = structlog.get_logger()


class DetectionService:
    """
    Service for detection operations

    Responsibilities:
    - Orchestrate detection workflow (scan AWS → run detectors → save to DB)
    - Manage detection lifecycle (list, get, filter)
    - Coordinate between AWS layer, detection algorithms, and database
    """

    async def run_scan(
        self,
        db: AsyncSession,
        resource_types: list[ResourceType],
        client_factory: AWSClientFactory | None = None,
    ) -> dict:
        """
        Run resource scan and save detections

        Args:
            db: Database session
            resource_types: List of resource types to scan (ec2_instance, ebs_volume, ebs_snapshot)
            client_factory: Optional AWS client factory (for dependency injection/testing)

        Returns:
            Scan results with total detections and savings
        """
        if client_factory is None:
            client_factory = AWSClientFactory()

        logger.info("Starting resource scan", resource_types=resource_types)

        try:
            # Step 1: Collect detections from AWS
            all_detections = await self._collect_detections(
                client_factory, resource_types
            )

            logger.info("Detections collected", count=len(all_detections))

            # Step 2: Save to database
            db_detections = await self._save_detections(db, all_detections)

            # Step 3: Calculate summary
            total_savings = sum(
                d.get("estimated_monthly_savings_inr", 0) for d in all_detections
            )

            logger.info(
                "Scan completed",
                total_detections=len(all_detections),
                total_savings_inr=total_savings,
            )

            return {
                "total_detections": len(all_detections),
                "total_savings_inr": total_savings,
                "detections": [d.to_dict() for d in db_detections],
            }

        except Exception as e:
            logger.exception("Scan failed", error=str(e), exc_info=True)
            raise

    async def _collect_detections(
        self,
        client_factory: AWSClientFactory,
        resource_types: list[ResourceType],
    ) -> list[dict]:
        """
        Collect detections from AWS using detection algorithms

        This method orchestrates the detection algorithms but doesn't contain
        the detection logic itself (that's in detection/ folder)
        """
        all_detections = []

        # EC2 Detection
        if ResourceType.EC2_INSTANCE in resource_types:
            try:
                ec2_detections = await self._detect_ec2_idle(client_factory)
                all_detections.extend(ec2_detections)
                logger.info("EC2 detections", count=len(ec2_detections))
            except Exception as e:
                logger.exception("EC2 detection failed", error=str(e))
                # Continue with other resource types

        # EBS Detection
        if ResourceType.EBS_VOLUME in resource_types:
            try:
                ebs_detections = await self._detect_ebs_unattached(client_factory)
                all_detections.extend(ebs_detections)
                logger.info("EBS detections", count=len(ebs_detections))
            except Exception as e:
                logger.exception("EBS detection failed", error=str(e))

        # Snapshot Detection
        if ResourceType.EBS_SNAPSHOT in resource_types:
            try:
                snapshot_detections = await self._detect_old_snapshots(client_factory)
                all_detections.extend(snapshot_detections)
                logger.info("Snapshot detections", count=len(snapshot_detections))
            except Exception as e:
                logger.exception("Snapshot detection failed", error=str(e))

        return all_detections

    async def _detect_ec2_idle(self, client_factory: AWSClientFactory) -> list[dict]:
        """Detect idle EC2 instances"""
        ec2_collector = EC2ResourceCollector(client_factory)
        ec2_detector = EC2IdleDetector(ec2_collector)
        return ec2_detector.detect_idle_instances()

    async def _detect_ebs_unattached(
        self, client_factory: AWSClientFactory
    ) -> list[dict]:
        """Detect unattached EBS volumes"""
        ebs_collector = EBSResourceCollector(client_factory)
        ebs_detector = EBSUnattachedDetector(ebs_collector)
        return ebs_detector.detect_unattached_volumes()

    async def _detect_old_snapshots(
        self, client_factory: AWSClientFactory
    ) -> list[dict]:
        """Detect old snapshots"""
        snapshot_collector = SnapshotCollector(client_factory)
        snapshot_detector = SnapshotDetector(snapshot_collector)
        return snapshot_detector.detect_old_snapshots()

    async def _save_detections(
        self,
        db: AsyncSession,
        detections: list[dict],
    ):
        """
        Save detections to database via repository

        Note: Transaction management is handled by the get_db() dependency
        """
        return await detection_repository.save_many(db, detections)

    async def list_detections(
        self,
        db: AsyncSession,
        status: str | None = None,
        resource_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        List detections with filters and pagination

        Args:
            db: Database session
            status: Filter by status
            resource_type: Filter by resource type
            limit: Page size
            offset: Pagination offset

        Returns:
            Paginated detection results
        """
        # Delegate to repository
        detections, total = await detection_repository.find_all(
            db=db,
            status=status,
            resource_type=resource_type,
            limit=limit,
            offset=offset,
        )

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "detections": [d.to_dict() for d in detections],
        }

    async def get_detection(
        self,
        db: AsyncSession,
        detection_id: int,
    ):
        """
        Get a specific detection by ID

        Args:
            db: Database session
            detection_id: Detection ID

        Returns:
            Detection object or None
        """
        return await detection_repository.find_by_id(db, detection_id)


# Singleton instance
detection_service = DetectionService()
