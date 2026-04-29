import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import client_id
from .lms_client import lms_client
from .center_ws import ws_loop
from .tasks import polling_task
from .routers import router

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting Edge Server with client ID: {client_id}")

    # Try using existing cookies first
    logger.info("Checking existing session...")
    # get_rollcalls will internally trigger login_ids() if cookies are expired (302/401)
    await lms_client.get_rollcalls()

    asyncio.create_task(polling_task())
    asyncio.create_task(ws_loop())
    yield
    # Shutdown
    await lms_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
