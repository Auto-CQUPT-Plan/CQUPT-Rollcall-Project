import asyncio
import logging
from .config import client_id, config
from .lms_client import lms_client
from .center_ws import send_to_center

logger = logging.getLogger(__name__)


async def polling_task():
    while True:
        try:
            rollcalls = await lms_client.get_rollcalls()
            if rollcalls:
                logger.info(
                    f"Polling: Found {len(rollcalls)} active rollcalls. Sharing with center..."
                )
                # Share with center
                await send_to_center(
                    {
                        "type": "share_rollcalls",
                        "client_id": client_id,
                        "rollcalls": rollcalls,
                    }
                )

                # Auto location checkin handling (placeholder for future)
                if config.auto_location_checkin:
                    for r in rollcalls:
                        if r["source"] == "radar" and r["status"] == "absent":
                            logger.info(
                                f"Auto location checkin enabled, but logic is pending implementation. Course: {r['course_title']}"
                            )
                            # payload = {"lat": ..., "lon": ...}
                            # await lms_client.do_checkin(r['rollcall_id'], "radar", payload)

        except Exception as e:
            logger.error(f"Polling task error: {e}")
        await asyncio.sleep(30)
