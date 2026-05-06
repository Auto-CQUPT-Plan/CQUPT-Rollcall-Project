import asyncio
import logging
import uvicorn
from edge_server.config import config, client_id

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_headless():
    from edge_server.lms_client import lms_client
    from edge_server.center_ws import ws_loop
    from edge_server.tasks import polling_task

    logger.info(
        f"Starting Edge Server in headless mode (no HTTP) with client ID: {client_id}"
    )

    # Try using existing cookies first
    await lms_client.get_rollcalls()

    try:
        # Run tasks and wait
        await asyncio.gather(polling_task(), ws_loop())
    finally:
        await lms_client.close()


def main():
    print("Starting CQUPT Rollcall Edge Server...")
    if config.http_port:
        uvicorn.run(
            "edge_server.edge_server:app", host="0.0.0.0", port=config.http_port
        )
    else:
        asyncio.run(run_headless())


if __name__ == "__main__":
    main()
