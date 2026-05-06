import asyncio
import json
import logging
import time
import websockets
from typing import Optional, Dict
from datetime import datetime, timezone

from .config import config, client_id
from .lms_client import lms_client
from .tasks import trigger_poll
from .utils import extract_qr_data

logger = logging.getLogger(__name__)

ws_connection: Optional[websockets.ClientConnection] = None

# Key -> timestamp of failure
invalid_shares: Dict[str, float] = {}


def is_in_invalid_cache(key: str) -> bool:
    if key in invalid_shares:
        if time.time() - invalid_shares[key] < 24 * 3600:
            return True
        else:
            del invalid_shares[key]
    return False


def add_to_invalid_cache(key: str):
    invalid_shares[key] = time.time()


async def send_to_center(message: dict):
    global ws_connection
    if not ws_connection:
        return
    try:
        logger.debug(f"Sending to center: {message}")
        await ws_connection.send(json.dumps(message))
    except Exception as e:
        logger.error(f"Failed to send to center server: {e}")


async def ws_loop():
    global ws_connection
    if not config.center_server_url:
        return
    while True:
        try:
            async with websockets.connect(config.center_server_url) as ws:
                ws_connection = ws
                logger.info("Connected to center server, sending register message")
                await ws.send(
                    json.dumps(
                        {
                            "type": "register",
                            "client_id": client_id,
                            "secret": config.center_server_secret,
                        }
                    )
                )
                trigger_poll()
                async for message in ws:
                    logger.info(f"Received from center: {message}")
                    data = json.loads(message)
                    if data.get("type") == "rollcall_share":
                        c_type = data.get("rollcall_type")
                        from_client_id = data.get("from_client_id")

                        rollcalls = await lms_client.get_rollcalls()
                        success = False

                        if c_type == "qr":
                            raw_qr_data = data.get("rollcall_qr_data")
                            cache_key = f"qr:{raw_qr_data}"
                            tried = False
                            c_data = None

                            if is_in_invalid_cache(cache_key):
                                logger.info(
                                    f"Skipping QR checkin (in invalid cache): {raw_qr_data}"
                                )
                                success = False
                            else:
                                c_data = extract_qr_data(raw_qr_data)
                                if not c_data:
                                    logger.warning(
                                        f"Received invalid QR data from center: {raw_qr_data}"
                                    )
                                    add_to_invalid_cache(cache_key)
                                    success = False
                                else:
                                    for r in rollcalls:
                                        if (
                                            r.get("source") == "qr"
                                            and r.get("status") == "absent"
                                        ):
                                            tried = True
                                            s, err = await lms_client.do_checkin(
                                                r["rollcall_id"], "qr", {"data": c_data}
                                            )
                                            if s:
                                                success = True

                                    if tried and not success:
                                        # Only cache as invalid if we actually tried and failed
                                        add_to_invalid_cache(cache_key)

                            if not tried:
                                continue

                            trigger_poll()
                            await send_to_center(
                                {
                                    "type": "rollcall_share_verification",
                                    "from_client_id": from_client_id,
                                    "client_id": client_id,
                                    "rollcall_type": "qr",
                                    "rollcall_qr_data": c_data,
                                    "valid": success,
                                    "timestamp": datetime.now(timezone.utc).strftime(
                                        "%Y-%m-%dT%H:%M:%SZ"
                                    ),
                                }
                            )

                        elif c_type == "number":
                            r_id = data.get("rollcall_id")
                            c_num = data.get("rollcall_number")
                            course_title = data.get("course_title", "")
                            course_location = data.get("course_location", None)

                            cache_key = f"num:{r_id}:{c_num}"
                            tried = False

                            if is_in_invalid_cache(cache_key):
                                logger.info(
                                    f"Skipping number checkin (in invalid cache): {r_id}:{c_num}"
                                )
                                success = False
                            else:
                                r = next(
                                    (
                                        r
                                        for r in rollcalls
                                        if r.get("rollcall_id") == r_id
                                    ),
                                    None,
                                )
                                if r and r.get("status") == "absent":
                                    tried = True
                                    s, err = await lms_client.do_checkin(
                                        r_id, "number", {"numberCode": str(c_num)}
                                    )
                                    if s:
                                        success = True
                                    else:
                                        add_to_invalid_cache(cache_key)
                                else:
                                    # Not in our tasks or already signed in
                                    success = False

                            if not tried:
                                continue

                            trigger_poll()
                            await send_to_center(
                                {
                                    "type": "rollcall_share_verification",
                                    "from_client_id": from_client_id,
                                    "client_id": client_id,
                                    "rollcall_type": "number",
                                    "course_title": course_title,
                                    "course_location": course_location,
                                    "rollcall_id": r_id,
                                    "rollcall_number": c_num,
                                    "valid": success,
                                    "timestamp": datetime.now(timezone.utc).strftime(
                                        "%Y-%m-%dT%H:%M:%SZ"
                                    ),
                                }
                            )
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            ws_connection = None
        await asyncio.sleep(5)
