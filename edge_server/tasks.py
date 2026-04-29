import asyncio
import logging
import json
import os
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional

from .config import client_id, config
from .lms_client import lms_client
from .center_ws import send_to_center

logger = logging.getLogger(__name__)

CURRICULUM_CACHE_FILE = os.path.join("data", "curriculum_cache.json")

# Global cache for curriculum
curriculum_data: Optional[Dict] = None
last_curriculum_fetch: Optional[datetime] = None


def get_location_coords(location_name: str) -> Optional[Dict[str, float]]:
    """
    TODO: Implement mapping from location names (e.g., '3403', '太极运动场02') to lat/lon.
    """
    # Placeholder mapping
    mapping = {
        "3403": {"lat": 29.531, "lon": 106.607},
        "3208": {"lat": 29.5315, "lon": 106.6075},
        "3211": {"lat": 29.5318, "lon": 106.6072},
        "太极运动场02": {"lat": 29.532, "lon": 106.608},
    }
    return mapping.get(location_name)


async def load_curriculum_from_file():
    global curriculum_data, last_curriculum_fetch
    if os.path.exists(CURRICULUM_CACHE_FILE):
        try:
            with open(CURRICULUM_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                curriculum_data = cached.get("data")
                updated_at_str = cached.get("_updated_at")
                if updated_at_str:
                    last_curriculum_fetch = datetime.fromisoformat(updated_at_str)
            logger.info("Loaded curriculum from local cache.")
        except Exception as e:
            logger.error(f"Failed to load curriculum cache: {e}")


async def fetch_curriculum():
    global curriculum_data, last_curriculum_fetch
    if not config.curriculum_api:
        return

    # Check if we need to fetch
    now = datetime.now()
    if last_curriculum_fetch and (now - last_curriculum_fetch) < timedelta(minutes=30):
        return

    try:
        logger.info("Fetching curriculum data from API...")
        resp = await lms_client.client.get(config.curriculum_api)
        if resp.status_code == 200:
            curriculum_data = resp.json()
            last_curriculum_fetch = now
            # Save to file
            with open(CURRICULUM_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "_updated_at": last_curriculum_fetch.isoformat(),
                        "data": curriculum_data,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info("Curriculum data updated and cached.")
        else:
            logger.error(f"Failed to fetch curriculum: {resp.status_code}")
    except Exception as e:
        logger.error(f"Error fetching curriculum: {e}")


def is_within_windows(now: time, windows: List[tuple]) -> bool:
    for start, end in windows:
        if start <= now <= end:
            return True
    return False


def should_poll() -> bool:
    now_dt = datetime.now()
    now_time = now_dt.time()

    if not config.curriculum_api:
        # Default windows
        windows = [
            (time(7, 50), time(12, 0)),
            (time(13, 50), time(18, 0)),
            (time(18, 50), time(22, 40)),
        ]
        return is_within_windows(now_time, windows)

    if not curriculum_data:
        return True  # Default to poll if we don't have data yet

    # Check curriculum for active courses
    today_str = now_dt.strftime("%Y-%m-%d")
    instances = curriculum_data.get("instances", [])
    for inst in instances:
        if inst.get("date") == today_str:
            try:
                start_dt = datetime.strptime(
                    f"{today_str} {inst['start_time']}", "%Y-%m-%d %H:%M"
                )
                end_dt = datetime.strptime(
                    f"{today_str} {inst['end_time']}", "%Y-%m-%d %H:%M"
                )

                # Polling window: config.curriculum_pre_minutes before start until end
                poll_start = start_dt - timedelta(minutes=config.curriculum_pre_minutes)
                if poll_start <= now_dt <= end_dt:
                    return True
            except (ValueError, KeyError):
                continue

    return False


def get_current_course_instance() -> Optional[Dict]:
    """Find the course instance that is currently active or about to start."""
    if not curriculum_data:
        return None
    now_dt = datetime.now()
    today_str = now_dt.strftime("%Y-%m-%d")
    instances = curriculum_data.get("instances", [])
    for inst in instances:
        if inst.get("date") == today_str:
            try:
                start_dt = datetime.strptime(
                    f"{today_str} {inst['start_time']}", "%Y-%m-%d %H:%M"
                )
                end_dt = datetime.strptime(
                    f"{today_str} {inst['end_time']}", "%Y-%m-%d %H:%M"
                )
                # Buffer for matching: 15 mins before start until end
                if (start_dt - timedelta(minutes=15)) <= now_dt <= end_dt:
                    return inst
            except (ValueError, KeyError):
                continue
    return None


async def polling_task():
    # Initial load
    await load_curriculum_from_file()

    while True:
        try:
            # 1. Update curriculum if needed (handled inside fetch_curriculum)
            if config.curriculum_api:
                await fetch_curriculum()

            # 2. Check if we should poll in this time slot
            if should_poll():
                rollcalls = await lms_client.get_rollcalls()
                if rollcalls:
                    logger.info(
                        f"Polling: Found {len(rollcalls)} active rollcalls. Sharing with center..."
                    )
                    await send_to_center(
                        {
                            "type": "share_rollcalls",
                            "client_id": client_id,
                            "rollcalls": rollcalls,
                        }
                    )

                    # 3. Auto Radar Check-in
                    if config.curriculum_api and config.auto_location_checkin:
                        # Index course by current time instead of matching name
                        current_inst = get_current_course_instance()
                        if current_inst:
                            for r in rollcalls:
                                if (
                                    r.get("source") == "radar"
                                    and r.get("status") == "absent"
                                ):
                                    # Basic verification: check if names match too, or just trust time?
                                    # Usually better to trust time but log if names differ
                                    if r.get("course_title") != current_inst.get(
                                        "course"
                                    ):
                                        logger.warning(
                                            f"Auto-radar: Time match found '{current_inst.get('course')}' but rollcall is '{r.get('course_title')}'"
                                        )

                                    location = current_inst.get("location")
                                    if location:
                                        coords = get_location_coords(location)
                                        if coords:
                                            logger.info(
                                                f"Auto-radar: Time-indexed course '{current_inst['course']}' at '{location}'. Attempting check-in..."
                                            )
                                            (
                                                success,
                                                error,
                                            ) = await lms_client.do_checkin(
                                                r["rollcall_id"], "radar", coords
                                            )
                                            if success:
                                                logger.info(
                                                    f"Auto-radar check-in successful for {r['course_title']}"
                                                )
                                            else:
                                                logger.warning(
                                                    f"Auto-radar check-in failed for {r['course_title']}: {error}"
                                                )
                                        else:
                                            logger.warning(
                                                f"Auto-radar: No coordinates found for location '{location}'"
                                            )
                        else:
                            # If no course in curriculum but rollcalls exist, we don't have location
                            pass

            else:
                # logger.debug("Outside polling windows. Skipping...")
                pass

        except Exception as e:
            logger.error(f"Polling task error: {e}")

        await asyncio.sleep(30)
