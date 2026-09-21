import asyncio
import json
import logging
import random
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_VP_SRC = Path(__file__).resolve().parent / "VisiblePlaywright" / "invisible_playwright" / "src"
if _VP_SRC.is_dir():
    sys.path.insert(0, str(_VP_SRC))

from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[RichHandler()]
)
logger = logging.getLogger("fb_commenter")
FACEBOOK_URL = "https://www.facebook.com/"
InvisiblePlaywright = None


def sanitize_error_text(value, secret="", max_length=400):
    text = str(value)
    if secret:
        text = text.replace(secret, "<redacted>")
    text = re.sub(
        r"(?i)(access_token|token|password|cookie)\s*[:=]\s*(?:\"[^\"\\r\\n]*\"|'[^'\\r\\n]*'|[^\\s,}]+)",
        r"\1=<redacted>",
        text,
    )
    text = re.sub(
        r"(?i)(?:bearer|oauth)\s+\S+",
        "Authorization <redacted>",
        text,
    )
    text = re.sub(
        r"(?i)(?:https?|socks5?)://[^/@\s]+:[^/@\s]+@",
        r"<proxy-redacted>@",
        text,
    )
    return re.sub(r"[\r\n]+", " ", text).strip()[:max_length]


class FacebookFanpageCommenter:
    def __init__(self, urls, cookies_file, comment_file, page_id, access_token=None, proxy=None, delay_min=1, delay_max=60, num_threads=3, headless=True, comment_mode="ui"):
        self.urls = self.parse_urls(urls)
        self.cookies_file = Path(cookies_file)
        self.comment_file = Path(comment_file)
        self.page_id = str(page_id).strip() if page_id else ""
        self.proxy = proxy
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.num_threads = num_threads
        self.headless = headless
        self.comments = self.load_comments()
        self.page = self.context = self.browser = self._launcher = None
        self._page_ready = False

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
        post_file = Path(__file__).resolve().parents[2] / "list UID" / "UID.txt"
        if not post_file.is_file():
            raise FileNotFoundError(f"Không tìm thấy file Post ID: {post_file}")
        post_ids = [
            line.strip()
            for line in post_file.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
        if not post_ids:
            raise ValueError(f"File Post ID đang trống: {post_file}")
        logger.info(f"Đã tải {len(post_ids)} Post ID")
        return post_ids

    def load_browser_cookies(self):
        raw = self.cookies_file.read_text(encoding="utf-8-sig").strip()
        if not raw:
            raise ValueError(f"File cookie đang trống: {self.cookies_file}")

        if raw.startswith("["):
            cookies = json.loads(raw)
            if not isinstance(cookies, list):
                raise ValueError("JSON cookie phải là một danh sách")
            return [self._normalize_cookie(cookie) for cookie in cookies]

        cookies = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") and not line.startswith("#HttpOnly_"):
                continue
            fields = line.split("\t")
            if len(fields) >= 7:
                domain = fields[0].removeprefix("#HttpOnly_")
                cookies.append({
                    "name": fields[5], "value": fields[6], "domain": domain,
                    "path": fields[2] or "/", "secure": fields[3].upper() == "TRUE"
                })
                continue
            for part in line.split(";"):
                if "=" in part:
                    name, value = part.split("=", 1)
                    if name.strip() and value.strip():
                        cookies.append({
                            "name": name.strip(), "value": value.strip(),
                            "domain": ".facebook.com", "path": "/"
                        })

        if not cookies:
            cookies = [{"name": "c_user", "value": raw, "domain": ".facebook.com", "path": "/"}]
        return cookies

    @staticmethod
    def _normalize_cookie(cookie):
        if not isinstance(cookie, dict) or not cookie.get("name") or "value" not in cookie:
            raise ValueError("Cookie JSON không hợp lệ")
        normalized = dict(cookie)
        normalized.setdefault("domain", ".facebook.com")
        normalized.setdefault("path", "/")
        normalized.pop("url", None)
        return normalized

    def _validate_page_post_id(self, value):
        owner_id = value.split("_", 1)[0]
        if not self.page_id or owner_id != self.page_id:
            raise ValueError("Post ID không thuộc Page ID đã cấu hình")
        return value

    def normalize_post_id(self, value):
        """Convert a Facebook post URL or ID to a Graph API object ID."""
        value = str(value).strip()
        if not value:
            raise ValueError("Post ID đang trống")

        if not value.startswith(("http://", "https://")):
            if value.startswith("pfbid"):
                raise ValueError("Post ID pfbid không được Graph API hỗ trợ; dùng object ID số")
            if re.fullmatch(r"\d+_\d+", value):
                return self._validate_page_post_id(value)
            raise ValueError("Cần Page post ID dạng page_id_post_id")

        parsed = urlsplit(value)
        if parsed.hostname not in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
            raise ValueError("URL bài viết không thuộc Facebook")
        query = parse_qs(parsed.query)
        story_id = query.get("story_fbid", [""])[0]
        owner_id = query.get("id", [self.page_id])[0]
        if story_id and owner_id and story_id.isdigit() and owner_id.isdigit():
            return self._validate_page_post_id(f"{owner_id}_{story_id}")

        parts = [part for part in parsed.path.split("/") if part]
        if "posts" in parts:
            post_index = parts.index("posts") + 1
            if post_index < len(parts) and parts[post_index].isdigit():
                post_id = parts[post_index]
                owner = parts[0] if parts[0].isdigit() else self.page_id
                if owner:
                    return self._validate_page_post_id(f"{owner}_{post_id}")
        raise ValueError("Không trích xuất được Post ID từ URL")

    def ui_target_url(self, value):
        """Facebook post URL or page_id_post_id that the browser can open."""
        value = str(value).strip()
        if value.startswith(("http://", "https://")):
            parsed = urlsplit(value)
            if parsed.hostname not in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
                raise ValueError("URL bài viết không thuộc Facebook")
            return value
        if re.fullmatch(r"\d+_\d+", value):
            page_id, post_id = self._validate_page_post_id(value).split("_", 1)
            return f"https://www.facebook.com/{page_id}/posts/{post_id}"
        if re.fullmatch(r"\d+", value):
            return f"https://www.facebook.com/{value}"
        raise ValueError("Target UI cần URL Facebook, UID số, hoặc Page post ID")

    def proxy_config(self):
        if not self.proxy:
            return None
        parsed = urlsplit(self.proxy)
        if not parsed.hostname:
            return {"server": self.proxy}
        port = f":{parsed.port}" if parsed.port else ""
        config = {"server": f"{parsed.scheme}://{parsed.hostname}{port}"}
        if parsed.username:
            config["username"] = parsed.username
            config["password"] = parsed.password or ""
        return config

    def _invisible_launcher(self):
        global InvisiblePlaywright
        if InvisiblePlaywright is None:
            from invisible_playwright.async_api import InvisiblePlaywright as Loaded
            InvisiblePlaywright = Loaded
        return InvisiblePlaywright(
            headless=bool(self.headless),
            proxy=self.proxy_config(),
        )

    async def login_with_cookie(self):
        logger.info("Đang login bằng cookie (InvisiblePlaywright)...")
        self._launcher = self._invisible_launcher()
        try:
            self.browser = await self._launcher.__aenter__()
            context = await self.browser.new_context()
            self.context = context
            await context.add_cookies(self.load_browser_cookies())
            self.page = await context.new_page()
            await self.page.goto(
                FACEBOOK_URL, wait_until="domcontentloaded", timeout=60000
            )
            await self.page.wait_for_timeout(1500)
            login_form = await self.page.locator('input[name="email"]').count()
            if "login" in self.page.url.lower() or login_form:
                raise RuntimeError(
                    "Cookie account không đăng nhập được; cần cookie còn hạn gồm c_user và xs"
                )
            logger.info("Đã mở Facebook")
            return context
        except BaseException:
            await self.close_browser()
            raise

    async def close_browser(self):
        """Close the InvisiblePlaywright session without leaking the browser."""
        context, launcher = self.context, self._launcher
        self.page = self.context = self.browser = self._launcher = None
        if context and launcher is None:
            try:
                await context.close()
            except BaseException as error:
                logger.debug("Context cleanup failed: %s", type(error).__name__)
        if launcher:
            try:
                await launcher.__aexit__(None, None, None)
            except BaseException as error:
                logger.debug("InvisiblePlaywright cleanup failed: %s", type(error).__name__)

    async def _switch_to_page(self):
        if not re.fullmatch(r"[0-9]+", self.page_id or ""):
            raise ValueError("Facebook Page ID không hợp lệ; phải là chuỗi số ASCII")
        await self.page.goto(
            f"https://www.facebook.com/{self.page_id}",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        switch_now = self.page.locator("button, [role='button']").filter(
            has_text=re.compile(r"Chuyển ngay|Switch now", re.I)
        )
        await self.page.wait_for_timeout(1500)
        if self._page_ready and not await switch_now.count():
            return
        if not await switch_now.count():
            raise RuntimeError("Không thấy nút chuyển sang Page")
        await switch_now.first.click()
        await self.page.wait_for_timeout(2500)
        if await switch_now.count():
            raise RuntimeError("Không xác nhận được danh tính Page")
        self._page_ready = True

    async def _set_comment_text(self, composer, comment_text):
        """Put the comment in the box once. Stealth fill() types it twice."""
        await composer.evaluate(
            """(el, text) => {
                el.focus();
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(el);
                selection.removeAllRanges();
                selection.addRange(range);
                document.execCommand('insertText', false, text);
                const written = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                if (written !== text) {
                    el.textContent = text;
                    el.dispatchEvent(new InputEvent('input', {
                        bubbles: true,
                        data: text,
                        inputType: 'insertText',
                    }));
                }
            }""",
            comment_text,
        )
        written = " ".join((await composer.inner_text()).split())
        if written != comment_text:
            raise RuntimeError("Ô comment không chứa đúng một bản nội dung")

    async def _post_comment_ui(self, post_id, comment_text):
        if not self.page:
            logger.warning("Bỏ qua comment: thiếu phiên Facebook")
            return False
        try:
            target = self.ui_target_url(post_id)
            await self._switch_to_page()
            await self.page.goto(target, wait_until="domcontentloaded", timeout=60000)
            composer = self.page.locator(
                '[contenteditable="true"][aria-label*="Bình luận"], '
                '[contenteditable="true"][aria-label*="comment" i]'
            ).first
            try:
                await composer.wait_for(state="visible", timeout=20000)
            except Exception:
                logger.warning("Không thấy ô comment trên bài viết")
                return False
            await composer.scroll_into_view_if_needed()
            await self._set_comment_text(composer, comment_text)
            await composer.press("Enter")
            posted = self.page.get_by_text(comment_text, exact=True)
            if not await posted.count():
                logger.warning("Không xác nhận được comment đã hiện trên bài")
                return False
            logger.info("Comment UI thành công")
            return True
        except (ValueError, RuntimeError) as error:
            logger.warning("Comment UI không thực hiện được: %s", error)
            return False

    async def post_comment(self, post_id, comment_text):
        return await self._post_comment_ui(post_id, comment_text)

    async def comment_random(self):
        post_ids = self.urls or self.load_uids()

        if not self.comments:
            logger.warning("Không có comment nào")
            return
        if not post_ids:
            logger.warning("Không có Post ID nào")
            return

        pool = list(dict.fromkeys(self.comments))
        for index, post_id in enumerate(post_ids):
            if not pool:
                logger.warning("Hết comment chưa dùng")
                return
            comment = random.choice(pool)
            pool.remove(comment)
            try:
                target = self.ui_target_url(post_id)
            except ValueError as error:
                logger.warning("Bỏ qua target không hợp lệ: %s", error)
                continue
            logger.info("Đang comment trên %s", target)
            success = await self.post_comment(post_id, comment)
            if not success:
                logger.warning("Comment không hiện trên %s", post_id)
                continue
            self.comments.remove(comment)
            if index == len(post_ids) - 1 or self.delay_max <= 0:
                continue
            delay = random.randint(self.delay_min * 60, self.delay_max * 60)
            logger.info("Đang delay %s phút...", delay // 60)
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                logger.info("Stopped by user")
                raise

    async def run(self):
        try:
            await self.login_with_cookie()
            await self.comment_random()
        finally:
            await self.close_browser()
            logger.info("Finished")
