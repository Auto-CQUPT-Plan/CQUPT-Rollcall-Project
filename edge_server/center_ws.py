import asyncio
import json
import logging
import websockets
from typing import Optional

from .config import config, client_id
from .lms_client import lms_client

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
                    if data.get("type") == "do_checkin":
                        r_id = data.get("rollcall_id")
                        c_type = data.get("source")
                        c_data = data.get("data")

                        # Validate we have this rollcall
                        rollcalls = await lms_client.get_rollcalls()
                        r = next(
                            (r for r in rollcalls if r["rollcall_id"] == r_id), None
                        )
                        if r and r["status"] == "absent":
                            payload = {}
                            if c_type == "qr":
                                payload["data"] = c_data
                            elif c_type == "number":
                                payload["numberCode"] = c_data

                            success, error = await lms_client.do_checkin(
                                r_id, c_type, payload
                            )
                            logger.info(
                                f"Center triggered checkin {r_id} ({c_type}): {'Success' if success else f'Failed ({error})'}"
                            )
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            ws_connection = None
        await asyncio.sleep(5)
