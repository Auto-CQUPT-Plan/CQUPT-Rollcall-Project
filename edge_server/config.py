import os
import json
import uuid
import logging
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DATA_DIR = "data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
CLIENT_ID_FILE = os.path.join(DATA_DIR, "client_id.txt")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


class Config(BaseModel):
    username: str
    password: str
    curriculum_api: str = ""
    curriculum_pre_minutes: int = 10
    http_port: Optional[int] = 8080
    center_server_url: str = ""
    center_server_secret: str = ""
    auto_location_checkin: bool = True


def load_config() -> Config:
    data = {}
    # 1. Try loading from file
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")

    # 2. Override with env vars
    env_mapping = {
        "username": "EDGE_USERNAME",
        "password": "EDGE_PASSWORD",
        "curriculum_api": "EDGE_CURRICULUM_API",
        "curriculum_pre_minutes": "EDGE_CURRICULUM_PRE_MINUTES",
        "http_port": "EDGE_HTTP_PORT",
        "center_server_url": "EDGE_CENTER_SERVER_URL",
        "center_server_secret": "EDGE_CENTER_SERVER_SECRET",
        "auto_location_checkin": "EDGE_AUTO_LOCATION_CHECKIN",
    }

    for field, env_name in env_mapping.items():
        val = os.environ.get(env_name)
        if val is not None:
            if field == "http_port":
                if val.strip() == "":
                    data[field] = None
                else:
                    try:
                        data[field] = int(val)
                    except ValueError:
                        logger.warning(
                            f"Env {env_name} must be an integer, got '{val}'"
                        )
            elif field == "curriculum_pre_minutes":
                try:
                    data[field] = int(val)
                except ValueError:
                    logger.warning(f"Env {env_name} must be an integer, got '{val}'")
            elif field == "auto_location_checkin":
                data[field] = val.lower() in ("true", "1", "yes")
            else:
                data[field] = val

    # 3. Validate required fields
    if not data.get("username") or not data.get("password"):
        if not os.path.exists(CONFIG_FILE):
            # Create a template if nothing exists
            default_config = Config(username="", password="")
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(default_config.model_dump_json(indent=2))
            logger.error(
                f"Required config (username/password) not found in {CONFIG_FILE} or env vars (EDGE_USERNAME/EDGE_PASSWORD)."
            )
        else:
            logger.error("Missing required config (username/password).")
        os._exit(1)

    return Config(**data)


def get_client_id() -> str:
    # 1. Env var priority
    env_id = os.environ.get("EDGE_CLIENT_ID")
    if env_id:
        return env_id

    # 2. File storage
    if os.path.exists(CLIENT_ID_FILE):
        try:
            with open(CLIENT_ID_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    # 3. Generate new
    new_id = str(uuid.uuid4())
    try:
        with open(CLIENT_ID_FILE, "w", encoding="utf-8") as f:
            f.write(new_id)
    except Exception as e:
        logger.warning(f"Could not save client ID to {CLIENT_ID_FILE}: {e}")
    return new_id


config = load_config()
client_id = get_client_id()
runtime_state = {"pause_shared_rollcall": False}
