import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .lms_client import lms_client
from .center_ws import send_to_center
from .config import client_id

logger = logging.getLogger(__name__)

router = APIRouter()


class CheckinPayload(BaseModel):
    data: Optional[str] = None
    numberCode: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


@router.get("/rollcalls")
async def api_get_rollcalls():
    return await lms_client.get_rollcalls()


@router.post("/rollcall/{rollcall_id}/qr")
async def api_checkin_qr(rollcall_id: int, payload: CheckinPayload):
    logger.info(f"API: Manual QR checkin for rollcall {rollcall_id}")
    if not payload.data:
        raise HTTPException(status_code=400, detail="Missing data field")
    success, error = await lms_client.do_checkin(
        rollcall_id, "qr", {"data": payload.data}
    )
    if success:
        rollcalls = await lms_client.get_rollcalls()
        r = next((x for x in rollcalls if x["rollcall_id"] == rollcall_id), None)
        course_id = r["course_id"] if r else 0
        await send_to_center(
            {
                "type": "checkin_data",
                "client_id": client_id,
                "course_id": course_id,
                "rollcall_id": rollcall_id,
                "source": "qr",
                "data": payload.data,
            }
        )
        return {"message": "success"}
    raise HTTPException(status_code=400, detail=error)


@router.post("/rollcall/{rollcall_id}/number")
async def api_checkin_number(rollcall_id: int, payload: CheckinPayload):
    if not payload.numberCode:
        raise HTTPException(status_code=400, detail="Missing numberCode field")
    success, error = await lms_client.do_checkin(
        rollcall_id, "number", {"numberCode": payload.numberCode}
    )
    if success:
        rollcalls = await lms_client.get_rollcalls()
        r = next((x for x in rollcalls if x["rollcall_id"] == rollcall_id), None)
        course_id = r["course_id"] if r else 0
        await send_to_center(
            {
                "type": "checkin_data",
                "client_id": client_id,
                "course_id": course_id,
                "rollcall_id": rollcall_id,
                "source": "number",
                "data": payload.numberCode,
            }
        )
        return {"message": "success"}
    raise HTTPException(status_code=400, detail=error)


@router.post("/rollcallqr")
async def api_rollcall_qr(payload: CheckinPayload):
    logger.info("API: Batch QR checkin starting...")
    if not payload.data:
        raise HTTPException(status_code=400, detail="Missing data field")

    rollcalls = await lms_client.get_rollcalls()
    results = []

    for r in rollcalls:
        if r.get("source") == "qr" and r.get("status") == "absent":
            rollcall_id = r["rollcall_id"]
            success, error = await lms_client.do_checkin(
                rollcall_id, "qr", {"data": payload.data}
            )
            if success:
                course_id = r.get("course_id", 0)
                await send_to_center(
                    {
                        "type": "checkin_data",
                        "client_id": client_id,
                        "course_id": course_id,
                        "rollcall_id": rollcall_id,
                        "source": "qr",
                        "data": payload.data,
                    }
                )
                results.append({"rollcall_id": rollcall_id, "status": "success"})
            else:
                results.append(
                    {"rollcall_id": rollcall_id, "status": "failed", "error": error}
                )

    return {"results": results}


@router.post("/rollcall/{rollcall_id}/location")
async def api_checkin_location(rollcall_id: int, payload: CheckinPayload):
    if payload.lat is None or payload.lon is None:
        raise HTTPException(status_code=400, detail="Missing lat or lon")
    data = {"lat": payload.lat, "lon": payload.lon}
    success, error = await lms_client.do_checkin(rollcall_id, "radar", data)
    if success:
        return {"message": "success"}
    raise HTTPException(status_code=400, detail=error)
