import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import httpx
from pydantic import BaseModel

# Configurable secrets
CENTER_SECRET = ""
EXTERNAL_SECRET_CONTROLLER = ""

app = FastAPI()


async def verify_secret(secret: str, client_id: str) -> bool:
    """
    Verify the secret either via external controller or static secret.
    """
    if EXTERNAL_SECRET_CONTROLLER:
        try:
            async with httpx.AsyncClient() as client:
                params = {"secret": secret, "uuid": client_id}
                resp = await client.get(EXTERNAL_SECRET_CONTROLLER, params=params)
                return resp.text.strip() == "success"
        except Exception as e:
            print(f"External secret verification failed: {e}")
            return False

    # Fallback to static secret if controller not configured
    if not CENTER_SECRET:
        return True
    return secret == CENTER_SECRET


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        # Already accepted in endpoint
        self.active_connections[websocket] = client_id

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    async def broadcast(self, message: dict):
        for ws in list(self.active_connections.keys()):
            try:
                await ws.send_json(message)
            except Exception:
                pass


class QRSubmit(BaseModel):
    data: str


manager = ConnectionManager()

# Global state
latest_qr_data: str = ""
latest_qr_timestamp: int = 0
qr_success_clients = set()
qr_needing_clients = set()

# rollcall_id -> {"course_title": "...", "rollcall_number": Optional[int], "updated_at": ...}
number_tasks: Dict[int, Dict[str, Any]] = {}


def update_qr_data(qr_string: str) -> bool:
    global latest_qr_data, latest_qr_timestamp, qr_success_clients
    if not is_qr_valid(qr_string):
        return False
    try:
        # Check first 10 digits as timestamp
        ts = int(qr_string[:10])
        if ts > latest_qr_timestamp:
            latest_qr_timestamp = ts
            latest_qr_data = qr_string
            return True
    except Exception:
        pass
    return False


def is_qr_valid(qr_data: str) -> bool:
    if not qr_data or len(qr_data) < 10:
        return False
    try:
        ts = int(qr_data[:10])
        return (time.time() - ts) <= 15
    except ValueError:
        return False


def get_current_status():
    is_valid = is_qr_valid(latest_qr_data)
    if is_valid:
        remaining = 15 - int(time.time() - latest_qr_timestamp)
    else:
        remaining = 0

    active_ids = set(manager.active_connections.values())

    # Exclude "unknown" connections that haven't registered
    active_ids.discard("unknown")

    # Only count clients that reported needing QR but haven't succeeded yet
    uncheckin = len(qr_needing_clients - qr_success_clients)

    return {
        "remaining_seconds": max(0, remaining),
        "current_qr": latest_qr_data if is_valid else "",
        "connected_edges": len(active_ids),
        "uncheckin_edges": uncheckin,
    }


def get_iso_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@app.get("/api/rollcall/")
async def index():
    return {"name": "CQUPT-Rollcall"}


@app.websocket("/api/rollcall/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = "unknown"
    try:
        data = await websocket.receive_json()
        print(f"Received initial message: {data}")
        if data.get("type") == "register":
            # Verify secret
            client_id = data.get("client_id", "unknown")
            client_secret = data.get("secret", "")

            if not await verify_secret(client_secret, client_id):
                print(f"Registration failed: Invalid secret from {client_id}")
                await websocket.send_json(
                    {"type": "error", "message": "Invalid secret"}
                )
                await websocket.close()
                return

            await manager.connect(websocket, client_id)
            print(f"Client {client_id} registered successfully")
        else:
            print("Registration failed: First message must be register")
            await websocket.send_json(
                {"type": "error", "message": "Registration required"}
            )
            await websocket.close()
            return
    except Exception as e:
        print(f"Error during registration: {e}")
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            print(f"Received message from {client_id}: {data}")
            msg_type = data.get("type")

            if msg_type == "rollcall_tasks":
                # Share latest QR if needed
                if (
                    data.get("rollcall_qr")
                    and latest_qr_data
                    and is_qr_valid(latest_qr_data)
                ):
                    await websocket.send_json(
                        {
                            "type": "rollcall_share",
                            "from_client_id": "center",
                            "rollcall_type": "qr",
                            "rollcall_qr_data": latest_qr_data,
                            "timestamp": get_iso_timestamp(),
                        }
                    )

                # Update if this client needs QR sign-in
                now_needs = bool(data.get("rollcall_qr"))
                if now_needs:
                    if client_id not in qr_needing_clients:
                        # New task or first time needing QR, reset success state
                        qr_success_clients.discard(client_id)
                    qr_needing_clients.add(client_id)
                else:
                    qr_needing_clients.discard(client_id)
                    qr_success_clients.discard(client_id)

                # Cache and check number tasks
                numbers = data.get("rollcall_number", [])
                for task in numbers:
                    r_id = task.get("rollcall_id")
                    title = task.get("course_title", "")
                    loc = task.get("course_location", None)
                    if r_id not in number_tasks:
                        number_tasks[r_id] = {
                            "course_title": title,
                            "course_location": loc,
                            "rollcall_number": None,
                            "updated_at": time.time(),
                        }
                    else:
                        number_tasks[r_id]["course_title"] = title
                        number_tasks[r_id]["course_location"] = loc
                        number_tasks[r_id]["updated_at"] = time.time()

                    # If center already knows the check-in number and it's valid within 24h, share it back
                    if number_tasks[r_id]["rollcall_number"] is not None:
                        if time.time() - number_tasks[r_id]["updated_at"] <= 24 * 3600:
                            await websocket.send_json(
                                {
                                    "type": "rollcall_share",
                                    "from_client_id": "center",
                                    "rollcall_type": "number",
                                    "course_title": title,
                                    "course_location": loc,
                                    "rollcall_id": r_id,
                                    "rollcall_number": number_tasks[r_id][
                                        "rollcall_number"
                                    ],
                                    "timestamp": get_iso_timestamp(),
                                }
                            )

            elif msg_type in ["rollcall_success", "rollcall_share_verification"]:
                r_type = data.get("rollcall_type")
                if r_type == "qr":
                    qr_str = data.get("rollcall_data") or data.get(
                        "rollcall_qr_data", ""
                    )
                    sender_id = data.get("client_id", "unknown")

                    if update_qr_data(qr_str):
                        qr_success_clients.add(sender_id)
                        await manager.broadcast(
                            {
                                "type": "rollcall_share",
                                "from_client_id": sender_id,
                                "rollcall_type": "qr",
                                "rollcall_qr_data": latest_qr_data,
                                "timestamp": get_iso_timestamp(),
                            }
                        )
                    elif qr_str == latest_qr_data:
                        qr_success_clients.add(sender_id)
                elif r_type == "number":
                    r_id = data.get("rollcall_id")
                    title = data.get("course_title", "")
                    loc = data.get("course_location", None)
                    num = data.get("rollcall_number")

                    if r_id not in number_tasks:
                        number_tasks[r_id] = {
                            "course_title": title,
                            "course_location": loc,
                            "rollcall_number": num,
                            "updated_at": time.time(),
                        }
                    else:
                        number_tasks[r_id]["course_title"] = title
                        number_tasks[r_id]["course_location"] = loc
                        number_tasks[r_id]["rollcall_number"] = num
                        number_tasks[r_id]["updated_at"] = time.time()

                    await manager.broadcast(
                        {
                            "type": "rollcall_share",
                            "from_client_id": data.get("client_id", "unknown"),
                            "rollcall_type": "number",
                            "course_title": title,
                            "course_location": loc,
                            "rollcall_id": r_id,
                            "rollcall_number": num,
                            "timestamp": get_iso_timestamp(),
                        }
                    )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        qr_needing_clients.discard(client_id)
        qr_success_clients.discard(client_id)


@app.websocket("/api/rollcall/ws/status")
async def websocket_status_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(get_current_status())
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass


@app.post("/api/rollcall/qr")
async def submit_qr(payload: QRSubmit):
    if update_qr_data(payload.data):
        await manager.broadcast(
            {
                "type": "rollcall_share",
                "from_client_id": "http_api",
                "rollcall_type": "qr",
                "rollcall_qr_data": latest_qr_data,
                "timestamp": get_iso_timestamp(),
            }
        )
    return {"message": "success", "latest_qr": latest_qr_data}


@app.get("/api/rollcall/status")
async def get_status():
    return get_current_status()
