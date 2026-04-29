import os
import json
import uuid
import logging
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
    http_port: int = 8080
    center_server_url: str = ""
    auto_location_checkin: bool = False


def load_config() -> Config:
    if not os.path.exists(CONFIG_FILE):
        default_config = Config(username="", password="")
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(default_config.model_dump_json(indent=2))
        logger.warning(f"Please fill in {CONFIG_FILE} and restart.")
        os._exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return Config(**json.load(f))


def get_client_id() -> str:
    if os.path.exists(CLIENT_ID_FILE):
        with open(CLIENT_ID_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    new_id = str(uuid.uuid4())
    with open(CLIENT_ID_FILE, "w", encoding="utf-8") as f:
        f.write(new_id)
    return new_id


config = load_config()
client_id = get_client_id()
