import logging
import re
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import asyncio
from .lms_client import lms_client
from .center_ws import send_to_center
from .config import client_id
from datetime import datetime, timezone
from .tasks import trigger_poll, get_course_location_for_rollcall

logger = logging.getLogger(__name__)

router = APIRouter()


from .utils import extract_qr_data


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

    qr_data = extract_qr_data(payload.data)
    if not qr_data:
        raise HTTPException(status_code=400, detail="Invalid QR code format")
    logger.info(f"QR Code Data: {qr_data}")

    success, error = await lms_client.do_checkin(rollcall_id, "qr", {"data": qr_data})
    if success:
        asyncio.create_task(
            send_to_center(
                {
                    "type": "rollcall_success",
                    "client_id": client_id,
                    "rollcall_type": "qr",
                    "rollcall_data": qr_data,
                    "timestamp": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
            )
        )
        trigger_poll()
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
        course_title = r["course_title"] if r else ""
        course_location = get_course_location_for_rollcall(r) if r else None
        asyncio.create_task(
            send_to_center(
                {
                    "type": "rollcall_success",
                    "client_id": client_id,
                    "rollcall_type": "number",
                    "course_title": course_title,
                    "course_location": course_location,
                    "rollcall_id": rollcall_id,
                    "rollcall_number": int(payload.numberCode),
                    "timestamp": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
            )
        )
        trigger_poll()
        return {"message": "success"}
    raise HTTPException(status_code=400, detail=error)


@router.post("/rollcallqr")
async def api_rollcall_qr(payload: CheckinPayload):
    logger.info("API: Batch QR checkin starting...")
    if not payload.data:
        raise HTTPException(status_code=400, detail="Missing data field")

    qr_data = extract_qr_data(payload.data)
    if not qr_data:
        raise HTTPException(status_code=400, detail="Invalid QR code format")
    logger.info(f"QR Code Data: {qr_data}")

    rollcalls = await lms_client.get_rollcalls()
    results = []

    for r in rollcalls:
        if r.get("source") == "qr" and r.get("status") == "absent":
            rollcall_id = r["rollcall_id"]
            success, error = await lms_client.do_checkin(
                rollcall_id, "qr", {"data": qr_data}
            )
            if success:
                asyncio.create_task(
                    send_to_center(
                        {
                            "type": "rollcall_success",
                            "client_id": client_id,
                            "rollcall_type": "qr",
                            "rollcall_data": qr_data,
                            "timestamp": datetime.now(timezone.utc).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                        }
                    )
                )
                trigger_poll()
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
        trigger_poll()
        return {"message": "success"}
    raise HTTPException(status_code=400, detail=error)
