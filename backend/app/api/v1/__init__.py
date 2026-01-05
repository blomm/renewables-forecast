"""API v1 routes."""

from fastapi import APIRouter
from app.api.v1 import calculate

api_router = APIRouter()

# Include route modules
api_router.include_router(calculate.router, prefix="/calculate", tags=["calculations"])
