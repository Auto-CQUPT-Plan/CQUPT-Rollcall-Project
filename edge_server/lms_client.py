import os
import json
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, Optional

from .config import config, client_id
from .crypto import encrypt_password

logger = logging.getLogger(__name__)

COOKIE_FILE = os.path.join("data", "cookies.json")


class LMSClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
            },
            follow_redirects=False,
        )
        self.load_cookies()

    def load_cookies(self):
        if os.path.exists(COOKIE_FILE):
            try:
                with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                    cookies_data = json.load(f)
                if isinstance(cookies_data, list):
                    for c in cookies_data:
                        self.client.cookies.set(
                            c["name"],
                            c["value"],
                            domain=c.get("domain"),
                            path=c.get("path"),
                        )
                elif isinstance(cookies_data, dict):
                    for k, v in cookies_data.items():
                        # Default to lms domain if unknown, as most important cookies are there
                        self.client.cookies.set(k, v, domain="lms.tc.cqupt.edu.cn")
                logger.info("Cookies loaded from file.")
            except Exception as e:
                logger.error(f"Failed to load cookies: {e}")

    def save_cookies_safe(self):
        try:
            cookies_list = []
            for cookie in self.client.cookies.jar:
                cookies_list.append(
                    {
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": cookie.domain,
                        "path": cookie.path,
                    }
                )
            with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                json.dump(cookies_list, f, indent=2)
            logger.info("Cookies saved to file.")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    async def login_ids(self) -> bool:
        logger.info("Attempting login...")
        try:
            # Clear current cookies for a fresh login if needed, or keep them?
            # Usually better to start fresh if we are explicitly logging in.
            self.client.cookies.clear()

            req = self.client.build_request("GET", "http://lms.tc.cqupt.edu.cn/login")
            for _ in range(2):
                resp = await self.client.send(req)
                if resp.next_request:
                    req = resp.next_request
                else:
                    break
            callback_url = req.url

            resp = await self.client.get(
                "https://ids.cqupt.edu.cn/authserver/login",
                params={"service": str(callback_url)},
            )
            soup = BeautifulSoup(resp.text, "html.parser")

            salt_input = soup.find("input", id="pwdEncryptSalt")
            if not salt_input:
                raise Exception("Login failed: cannot find salt")
            salt = salt_input.get("value")

            execution_input = soup.find("input", attrs={"name": "execution"})
            if not execution_input:
                raise Exception("Login failed: cannot find execution")
            execution = execution_input.get("value")

            data = {
                "username": config.username,
                "password": encrypt_password(config.password, salt),
                "captcha": "",
                "_eventId": "submit",
                "cllt": "userNameLogin",
                "dllt": "generalLogin",
                "lt": "",
                "execution": execution,
            }

            resp2 = await self.client.post(
                "https://ids.cqupt.edu.cn/authserver/login",
                params={"service": str(callback_url)},
                data=data,
            )

            redirect_url = None
            if resp2.status_code == 302:
                redirect_url = str(resp2.headers.get("Location"))
            elif resp2.status_code == 200 and "踢出会话" in resp2.text:
                soup2 = BeautifulSoup(resp2.text, "html.parser")
                exec2_input = soup2.find("input", attrs={"name": "execution"})
                if exec2_input:
                    exec2 = exec2_input.get("value")
                    resp3 = await self.client.post(
                        "https://ids.cqupt.edu.cn/authserver/login",
                        params={"service": str(callback_url)},
                        data={"execution": exec2, "_eventId": "continue"},
                    )
                    if resp3.status_code == 302:
                        redirect_url = str(resp3.headers.get("Location"))

            if redirect_url:
                await self.client.get(redirect_url, follow_redirects=True)
                # Check session
                for c in self.client.cookies.jar:
                    if c.domain == "lms.tc.cqupt.edu.cn" and c.name == "session":
                        logger.info("Login successful")
                        self.save_cookies_safe()
                        return True

            logger.error("Login failed or no session cookie found")
            return False
        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            return False

    async def get_rollcalls(self) -> List[Dict]:
        url = "http://lms.tc.cqupt.edu.cn/api/radar/rollcalls"
        params = {"api_version": "1.1.0"}
        try:
            resp = await self.client.get(url, params=params)
            # 302 to identity or 401 Unauthorized both mean session expired
            if resp.status_code == 302 or resp.status_code == 401:
                logger.info(f"Session expired ({resp.status_code}), re-logging in...")
                if await self.login_ids():
                    resp = await self.client.get(url, params=params)
                    if resp.status_code != 200:
                        return []
                else:
                    return []
            elif resp.status_code != 200:
                logger.error(f"Failed to fetch rollcalls: {resp.status_code}")
                return []
            return resp.json().get("rollcalls", [])
        except Exception as e:
            logger.error(f"Error fetching rollcalls: {e}")
            return []

    async def do_checkin(
        self, rollcall_id: int, type_: str, payload: dict
    ) -> Tuple[bool, Optional[str]]:
        """Returns (success, error_code_or_message)"""
        payload["deviceId"] = client_id
        if type_ == "qr":
            url = f"http://lms.tc.cqupt.edu.cn/api/rollcall/{rollcall_id}/answer_qr_rollcall"
        elif type_ == "number":
            url = f"http://lms.tc.cqupt.edu.cn/api/rollcall/{rollcall_id}/answer_number_rollcall"
        elif type_ == "radar":
            url = f"http://lms.tc.cqupt.edu.cn/api/rollcall/{rollcall_id}/answer"
        else:
            return False, "Invalid checkin type"

        try:
            logger.info(f"Executing {type_} checkin for rollcall {rollcall_id}...")
            resp = await self.client.put(url, json=payload)
            data = resp.json()
            if resp.status_code == 200 and data.get("status") == "on_call":
                logger.info(f"Checkin successful for rollcall {rollcall_id}")
                return True, None

            error_code = (
                data.get("error_code") or data.get("message") or "Unknown error"
            )
            logger.warning(
                f"Checkin failed for rollcall {rollcall_id}: {resp.status_code} - {error_code}"
            )
            return False, error_code
        except Exception as e:
            logger.error(f"Checkin exception for rollcall {rollcall_id}: {e}")
            return False, str(e)

    async def close(self):
        await self.client.aclose()


lms_client = LMSClient()
