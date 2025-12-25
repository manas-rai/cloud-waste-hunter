"""
API v1 Router
"""

from fastapi import APIRouter

from app.api.v1 import actions, audit, detections

api_router = APIRouter()

api_router.include_router(detections.router, prefix="/detections", tags=["detections"])
api_router.include_router(actions.router, prefix="/actions", tags=["actions"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
