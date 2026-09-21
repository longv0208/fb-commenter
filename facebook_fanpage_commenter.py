import asyncio
import random
import logging
import time
import json
from pathlib import Path
from playwright.async_api import async_playwright
from rich.logging import RichHandler
import httpx
import uuid
import base64
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[RichHandler()]
)
logger = logging.getLogger("fb_commenter")

class FacebookFanpageCommenter:
    def __init__(self, urls, cookies_file, comment_file, page_id, access_token=None, proxy=None, delay_min=1, delay_max=60, num_threads=3, headless=True):
        self.urls = self.parse_urls(urls)
        self.cookies_file = Path(cookies_file)
        self.comment_file = Path(comment_file)
        self.page_id = page_id
        self.access_token = access_token or "YOUR_PAGE_ACCESS_TOKEN"
        self.proxy = proxy
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.num_threads = num_threads
        self.headless = headless
        self.comments = self.load_comments()
        self.page = None

    def parse_urls(self, urls_str):
        if not urls_str:
            return []
        return [url.strip() for url in urls_str.split(",") if url.strip()]

    def load_comments(self):
        if not self.comment_file.exists():
            raise FileNotFoundError(f"File comment_list.txt không tồn tại: {self.comment_file}")
        with open(self.comment_file, "r", encoding="utf-8") as f:
            comments = [line.strip() for line in f if line.strip()]
        logger.info(f"Đã tải {len(comments)} comment")
        return comments

    def load_uids(self):
        uid_file = Path(__file__).parent.parent / "list UID" / "UID.txt"
        if uid_file.exists():
            with open(uid_file, "r", encoding="utf-8") as f:
                uids = [line.strip() for line in f if line.strip()]
            logger.info(f"Đã tải {len(uids)} UID")
            return uids
        else:
            logger.warning("Không tìm thấy file UID.txt, dùng UID mặc định")
            return ["1234567890", "9876543210"]

    async def login_with_cookie(self):
        logger.info("Đang login bằng cookie (Chrome)...")
        playwright = await async_playwright().start()

        # Launch browser with proxy if exists
        launch_args = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"]
        }

        if self.proxy:
            launch_args["proxy"] = {"server": self.proxy}

        browser = await playwright.chromium.launch(**launch_args)
        context = await browser.new_context()

        # Load cookies
        cookies = []
        with open(self.cookies_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cookies.append({"name": "c_user", "value": line.strip(), "url": "https://www.facebook.com"})

        await context.add_cookies(cookies)
        self.page = await context.new_page()

        logger.info("Login thành công bằng cookie")
        return context

    async def post_comment(self, post_id, comment_text):
        if not self.page:
            return False

        try:
            # Comment bằng Graph API (nhanh hơn)
            url = f"https://graph.facebook.com/v18.0/{post_id}/feed"
            payload = {
                "message": comment_text,
                "access_token": self.access_token
            }

            # Nếu có proxy, dùng httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=payload)

            if response.status_code == 200:
                logger.info(f"Comment thành công: {comment_text}")
                return True
            else:
                logger.warning(f"Comment thất bại: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Lỗi khi comment: {e}")
            return False

    async def comment_random(self):
        uids = self.load_uids()

        if not self.comments:
            logger.warning("Không có comment nào")
            return

        while self.comments:
            comment = random.choice(self.comments)
            uid = random.choice(uids)

            post_id = uid  # UID làm post_id

            logger.info(f"Đang comment: {comment} trên UID {uid}")

            success = await self.post_comment(post_id, comment)
            if success:
                self.comments.remove(comment)

            delay = random.randint(self.delay_min * 60, self.delay_max * 60)
            logger.info(f"Đang delay {delay // 60} phút...")
            await asyncio.sleep(delay)

    async def run(self):
        context = await self.login_with_cookie()
        try:
            await self.comment_random()
        finally:
            await context.close()
            logger.info("Hoàn tất công việc")

# Example usage
if __name__ == "__main__":
    import asyncio
    async def test():
        commenter = FacebookFanpageCommenter(
            urls="1234567890,9876543210",
            cookies_file="cookies.txt",
            comment_file="comment_list.txt",
            page_id="1234567890",
            proxy="http://user:pass@proxy-ip:port",
            delay_min=1,
            delay_max=5,
            num_threads=2,
            headless=True
        )
        await commenter.run()
    asyncio.run(test())