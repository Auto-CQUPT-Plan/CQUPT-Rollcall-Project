import asyncio
import json
import logging
import websockets
from typing import Optional
from datetime import datetime, timezone

from .config import config, client_id
from .lms_client import lms_client
from .tasks import trigger_poll

logger = logging.getLogger(__name__)

ws_connection: Optional[websockets.ClientConnection] = None


async def send_to_center(message: dict):
    global ws_connection
    if ws_connection and not ws_connection.closed:
        try:
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
                logger.info("Connected to center server")
                await ws.send(json.dumps({"type": "register", "client_id": client_id}))
                async for message in ws:
                    data = json.loads(message)
                    if data.get("type") == "rollcall_share":
                        c_type = data.get("rollcall_type")
                        from_client_id = data.get("from_client_id")

                        rollcalls = await lms_client.get_rollcalls()
                        success = False

                        if c_type == "qr":
                            c_data = data.get("rollcall_qr_data")
                            for r in rollcalls:
                                if (
                                    r.get("source") == "qr"
                                    and r.get("status") == "absent"
                                ):
                                    s, err = await lms_client.do_checkin(
                                        r["rollcall_id"], "qr", {"data": c_data}
                                    )
                                    if s:
                                        success = True

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
                            r = next(
                                (r for r in rollcalls if r.get("rollcall_id") == r_id),
                                None,
                            )
                            if r and r.get("status") == "absent":
                                s, err = await lms_client.do_checkin(
                                    r_id, "number", {"numberCode": str(c_num)}
                                )
                                if s:
                                    success = True

                            trigger_poll()
                            await send_to_center(
                                {
                                    "type": "rollcall_share_verification",
                                    "from_client_id": from_client_id,
                                    "client_id": client_id,
                                    "rollcall_type": "number",
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
