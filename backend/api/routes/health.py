from fastapi import APIRouter, HTTPException

from services import health_service

router = APIRouter()


@router.get("/live")
async def live() -> dict:
    return health_service.get_live_status()


@router.get("/ready")
async def ready() -> dict:
    readiness = health_service.get_readiness_status()
    if readiness["status"] != "ready":
        raise HTTPException(status_code=503, detail=readiness)
    return readiness
