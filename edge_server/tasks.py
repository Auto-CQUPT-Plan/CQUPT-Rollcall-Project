import asyncio
import logging
import json
import os
import random
from datetime import datetime, time, timedelta, timezone
from typing import List, Dict, Optional

from .config import client_id, config
from .lms_client import lms_client
from .center_ws import send_to_center

logger = logging.getLogger(__name__)

CURRICULUM_CACHE_FILE = os.path.join("data", "curriculum_cache.json")

# Global cache for curriculum
curriculum_data: Optional[Dict] = None
last_curriculum_fetch: Optional[datetime] = None
poll_trigger_event: Optional[asyncio.Event] = None


def trigger_poll():
    if poll_trigger_event:
        poll_trigger_event.set()


def get_location_coords(location_name: str) -> Optional[Dict[str, float]]:
    teaching_building_positions = {
        "1": {
            "poiid": "B0JGP7JVZ3",
            "name": "重庆邮电大学一教学楼",
            "address": "重庆市南岸区南山街道崇文路2号",
            "telephone": "",
            "x": "106.605647",
            "y": "29.531049",
            "classify": "门牌信息",
        },
        "2": {
            "poiid": "B00170AKOO",
            "name": "重庆邮电大学老二教学楼",
            "address": "重庆市南岸区南山街道崇文路2号",
            "telephone": "",
            "x": "106.606620",
            "y": "29.532345",
            "classify": "门牌信息",
        },
        "3": {
            "poiid": "B00170AKOS",
            "name": "重庆邮电大学第三教学楼",
            "address": "重庆市南岸区南山街道崇文路2号",
            "telephone": "",
            "x": "106.609243",
            "y": "29.535101",
            "classify": "门牌信息",
        },
        "4": {
            "poiid": "B001793EEX",
            "name": "重庆邮电大学四教学楼",
            "address": "重庆市南岸区南山街道崇文路2号",
            "telephone": "",
            "x": "106.609269",
            "y": "29.536307",
            "classify": "门牌信息",
        },
        "5": {
            "poiid": "B0JGP7KB5J",
            "name": "重庆邮电大学五教学楼",
            "address": "重庆市南岸区南山街道崇文路2号",
            "telephone": "",
            "x": "106.610354",
            "y": "29.536018",
            "classify": "门牌信息",
        },
        "8": {
            "poiid": "B0MGBUTIQF",
            "name": "重庆邮电大学第八教学楼",
            "address": "重庆市南岸区崇文路2号重庆邮电大学内",
            "telephone": "",
            "x": "106.611013",
            "y": "29.534461",
            "classify": "科教文化场所",
        },
        "9": {
            "poiid": "B0LK6SKEQB",
            "name": "重庆邮电大学第九教学楼",
            "address": "重庆市南岸区新市场支路与南山路交叉口东340米",
            "telephone": "",
            "x": "106.606189",
            "y": "29.525971",
            "classify": "科教文化场所",
        },
    }

    other_building_positions = {
        "综合实验楼A": {
            "poiid": "B0JGP7KB5G",
            "name": "重庆邮电大学综合实验楼A幢",
            "address": "重庆市南岸区南山街道崇文路2号",
            "telephone": "",
            "x": "106.605528",
            "y": "29.525598",
            "classify": "门牌信息",
        },
        "综合实验楼B": {
            "poiid": "B0FFJ2TSDW",
            "name": "重庆邮电大学综合实验楼B幢",
            "address": "重庆市南岸区南山街道崇文路2号",
            "telephone": "",
            "x": "106.605611",
            "y": "29.525013",
            "classify": "门牌信息",
        },
        "综合实验楼C": {
            "poiid": "B0FFH453LD",
            "name": "重庆邮电大学综合实验楼C幢",
            "address": "重庆市南岸区南山街道崇文路2号",
            "telephone": "",
            "x": "106.605629",
            "y": "29.524309",
            "classify": "门牌信息",
        },
        "桂花篮球场": {
            "poiid": "B0HRVODGXX",
            "name": "重庆邮电大学-桂花篮球场",
            "address": "重庆市南岸区崇文路2号重庆邮电大学内(三教学楼旁)",
            "telephone": "",
            "x": "106.607208",
            "y": "29.530162",
            "classify": "运动场馆",
        },
        "灯光篮球场": {
            "poiid": "B0L2LSP7HG",
            "name": "重庆邮电大学灯光篮球场",
            "address": "重庆市南岸区重庆邮电大学玉兰园东南侧170米",
            "telephone": "",
            "x": "106.608514",
            "y": "29.532465",
            "classify": "体育休闲场所",
        },
        "风华运动场": {
            "poiid": "B0JGP7JVZ7",
            "name": "重庆邮电大学风华运动场",
            "address": "重庆市南岸区南山街道崇文路2号重庆邮电大学",
            "telephone": "",
            "x": "106.607568",
            "y": "29.532786",
            "classify": "运动场所",
        },
        "太极运动场": {
            "poiid": "B00170C5ZJ",
            "name": "重庆邮电大学太极运动场",
            "address": "重庆市南岸区南山街道崇文路2号重庆邮电大学",
            "telephone": "",
            "x": "106.609731",
            "y": "29.532896",
            "classify": "运动场所",
        },
    }

    target = None
    # 1. 4位数字地名逻辑：取首位匹配教学楼
    if location_name.isdigit() and len(location_name) == 4:
        building_num = location_name[0]
        target = teaching_building_positions.get(building_num)

    # 2. 关键词包含检测
    if not target:
        for keyword, pos in other_building_positions.items():
            if keyword in location_name:
                target = pos
                break

    if target:
        try:
            # 数据中的 x 为经度 (lon)，y 为纬度 (lat)
            base_lon = float(target["x"])
            base_lat = float(target["y"])

            # 3. 增加一点随机精度 (约 +/- 20米范围)
            jitter_lat = (random.random() - 0.2) * 0.0008
            jitter_lon = (random.random() - 0.2) * 0.0008

            return {"lat": base_lat + jitter_lat, "lon": base_lon + jitter_lon}
        except (ValueError, KeyError):
            return None

    return None


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
    global poll_trigger_event
    if poll_trigger_event is None:
        poll_trigger_event = asyncio.Event()

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
                    has_qr = any(
                        r.get("source") == "qr" and r.get("status") == "absent"
                        for r in rollcalls
                    )
                    numbers = [
                        r["rollcall_id"]
                        for r in rollcalls
                        if r.get("source") == "number" and r.get("status") == "absent"
                    ]
                    await send_to_center(
                        {
                            "type": "rollcall_tasks",
                            "client_id": client_id,
                            "rollcall_qr": has_qr,
                            "rollcall_number": numbers,
                            "timestamp": datetime.now(timezone.utc).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
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

        try:
            await asyncio.wait_for(poll_trigger_event.wait(), timeout=30)
            poll_trigger_event.clear()
        except asyncio.TimeoutError:
            pass
