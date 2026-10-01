from __future__ import annotations

from fastapi import APIRouter, Depends

from app.interfaces.api.payments import router as payments_router
from app.interfaces.api.security import verify_api_key

api_v1_router = APIRouter(dependencies=[Depends(verify_api_key)])
api_v1_router.include_router(payments_router, prefix="/api/v1")
