"""
Detection Repository - Data access for Detection model
"""

from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.detection import Detection, DetectionStatus
import structlog

logger = structlog.get_logger()


class DetectionRepository:
    """
    Repository for Detection model
    
    Encapsulates all database operations for Detection entity.
    Service layer uses this instead of direct database queries.
    """

    async def find_all(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Detection], int]:
        """
        Find detections with filters and pagination
        
        Args:
            db: Database session
            status: Filter by status
            resource_type: Filter by resource type
            limit: Page size
            offset: Pagination offset
            
        Returns:
            Tuple of (detections list, total count)
        """
        # Build query
        stmt = select(Detection)
        
        if status:
            stmt = stmt.where(Detection.status == DetectionStatus(status))
        
        if resource_type:
            stmt = stmt.where(Detection.resource_type == resource_type)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.order_by(Detection.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        detections = result.scalars().all()
        
        return list(detections), total

    async def find_by_id(
        self,
        db: AsyncSession,
        detection_id: int,
    ) -> Optional[Detection]:
        """
        Find detection by ID
        
        Args:
            db: Database session
            detection_id: Detection ID
            
        Returns:
            Detection object or None
        """
        stmt = select(Detection).where(Detection.id == detection_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_ids(
        self,
        db: AsyncSession,
        detection_ids: List[int],
    ) -> List[Detection]:
        """
        Find multiple detections by IDs
        
        Args:
            db: Database session
            detection_ids: List of detection IDs
            
        Returns:
            List of Detection objects
        """
        stmt = select(Detection).where(Detection.id.in_(detection_ids))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def save_many(
        self,
        db: AsyncSession,
        detections: List[Dict],
    ) -> List[Detection]:
        """
        Bulk save detections
        
        Args:
            db: Database session
            detections: List of detection dictionaries
            
        Returns:
            List of saved Detection objects
        """
        from datetime import datetime, timezone
        
        db_detections = []
        now = datetime.now(timezone.utc)
        
        for detection in detections:
            db_detection = Detection(
                resource_type=detection["resource_type"],
                resource_id=detection["resource_id"],
                resource_name=detection.get("resource_name"),
                region=detection["region"],
                confidence_score=detection["confidence_score"],
                estimated_monthly_savings_inr=detection["estimated_monthly_savings_inr"],
                status=DetectionStatus.PENDING,
                meta_data=detection.get("metadata", {}),
                created_at=now,
                updated_at=now,
            )
            db.add(db_detection)
            db_detections.append(db_detection)
        
        # Flush to get IDs
        await db.flush()
        
        # Refresh to load generated fields
        for db_detection in db_detections:
            await db.refresh(db_detection)
        
        logger.info("Saved detections to database", count=len(db_detections))
        
        return db_detections

    async def update(
        self,
        db: AsyncSession,
        detection: Detection,
    ) -> Detection:
        """
        Update detection
        
        Args:
            db: Database session
            detection: Detection object to update
            
        Returns:
            Updated Detection object
        """
        await db.flush()
        await db.refresh(detection)
        return detection

    async def delete(
        self,
        db: AsyncSession,
        detection_id: int,
    ) -> bool:
        """
        Delete detection by ID
        
        Args:
            db: Database session
            detection_id: Detection ID
            
        Returns:
            True if deleted, False if not found
        """
        detection = await self.find_by_id(db, detection_id)
        if detection:
            await db.delete(detection)
            await db.flush()
            return True
        return False

    async def count_by_status(
        self,
        db: AsyncSession,
        status: DetectionStatus,
    ) -> int:
        """
        Count detections by status
        
        Args:
            db: Database session
            status: Detection status
            
        Returns:
            Count of detections
        """
        stmt = select(func.count()).select_from(Detection).where(Detection.status == status)
        result = await db.execute(stmt)
        return result.scalar_one()


# Singleton instance
detection_repository = DetectionRepository()

