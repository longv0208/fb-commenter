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

_GROUP_POST_SCRIPT = """
() => {
  const messageText = (box) => {
    const preferred = box.querySelectorAll('[data-ad-preview="message"], [data-ad-comet-preview="message"], [data-ad-rendering-role="story_message"]');
    if (preferred.length) {
      return Array.from(preferred).map((el) => (el.innerText || '').trim()).filter(Boolean).join('\\n').slice(0, 2000);
    }
    const lines = [];
    for (const el of box.querySelectorAll('div[dir="auto"], span[dir="auto"]')) {
      const line = (el.innerText || '').replace(/\\s+/g, ' ').trim();
      if (line.length < 2 || /^facebook$/i.test(line)) continue;
      if (lines.some((item) => item.includes(line) || line.includes(item))) continue;
      lines.push(line);
    }
    if (lines.length) return lines.join('\\n').slice(0, 2000);
    return (box.innerText || '').replace(/facebook/gi, ' ').replace(/\\s+/g, ' ').trim().slice(0, 2000);
  };
  const posts = [];
  const seen = new Set();
  let cardSeq = 0;
  const markCard = (start) => {
    // Gắn ID trực tiếp lên element chứa post — đừng bubble lên ancestor,
    // vì ancestor có thể bao nhiều bài → click nhầm nút của bài khác.
    const id = String(++cardSeq);
    start.setAttribute('data-fb-card', id);
    return id;
  };
  const groupMatch = location.pathname.match(/\\/groups\\/([^/]+)/);
  const groupSlug = groupMatch ? groupMatch[1] : '';
  const articles = document.querySelectorAll('[role="article"]');
  const urlFrom = (html) => {
    const marker = '/groups/';
    let start = html.indexOf(marker);
    while (start >= 0) {
      const slice = html.slice(start, start + 220);
      const end = slice.search(/["'\\s?#]/);
      const path = (end > 0 ? slice.slice(0, end) : slice).replace(/&amp;/g, '&');
      if (path.includes('/posts/')) return 'https://www.facebook.com' + path.split('?')[0];
      start = html.indexOf(marker, start + marker.length);
    }
    const pfbid = html.match(/pfbid[0-9A-Za-z]+/);
    if (pfbid && groupSlug) {
      return 'https://www.facebook.com/groups/' + groupSlug + '/posts/' + pfbid[0];
    }
    return '';
  };
  for (const article of articles) {
    let href = '';
    for (const anchor of article.querySelectorAll('a[href], [role="link"]')) {
      const raw = anchor.href || '';
      const id = raw.match(/\\/(?:posts|permalink)\\/([^/?#]+)/)
        || raw.match(/[?&](?:multi_permalinks|story_fbid)=([^&#]+)/)
        || raw.match(/pcb\\.(\\d+)/);
      if (!id) continue;
      const postId = decodeURIComponent(id[1]);
      href = groupSlug
        ? 'https://www.facebook.com/groups/' + groupSlug + '/posts/' + postId
        : raw.split('?')[0];
      break;
    }
    if (!href) href = urlFrom(article.innerHTML || '');
    if (!href || seen.has(href) || !href.includes('/groups/' + groupSlug + '/')) continue;
    const box = article;
    const story = box.querySelector('[data-ad-rendering-role="story_message"]');
    const photo = box.querySelector('a[href*="set=gm."], a[href*="set=pcb."]');
    if (!story && !photo) continue;
    const alts = Array.from(box.querySelectorAll('img'))
      .map((img) => (img.alt || '').trim())
      .filter((alt) => alt && !/^facebook$/i.test(alt));
    const text = (story ? (story.innerText || '').trim() : [messageText(box), ...alts].filter(Boolean).join('\\n')).slice(0, 2000);
    const images = Array.from(box.querySelectorAll('img'))
      .filter((img) => img.src && (img.naturalWidth || img.width || 0) > 40)
      .length;
    if (text.length < 2 && images === 0) continue;
    box.setAttribute('data-fb-post', href);
    seen.add(href);
    let authorId = '';
    for (const link of box.querySelectorAll('a[href]')) {
      const match = link.href.match(/profile\\.php\\?id=(\\d+)/) || link.href.match(/\\/user\\/(\\d+)/);
      if (match) {
        authorId = match[1];
        break;
      }
    }
    posts.push({ post_url: href, text: text, author_id: authorId, image_count: images, card_id: markCard(box) });
  }
  for (const anchor of document.querySelectorAll('a[href*="set=gm."], a[href*="set=pcb."]')) {
    const id = anchor.href.match(/set=(?:gm|pcb)\\.(\\d+)/);
    if (!id || !groupSlug) continue;
    const href = 'https://www.facebook.com/groups/' + groupSlug + '/posts/' + id[1];
    if (seen.has(href)) continue;
    seen.add(href);
    // card = article[role=article] gần nhất chứa anchor → action bar của đúng bài
    let box = anchor.closest('[role="article"]');
    if (!box) {
      box = anchor;
      let node = anchor;
      for (let i = 0; i < 12 && node.parentElement; i += 1) {
        const parent = node.parentElement;
        if ((parent.innerText || '').length > 2500) break;
        node = parent;
        box = parent;
      }
    }
    box.setAttribute('data-fb-post', href);
    const text = messageText(box).slice(0, 2000);
    const images = Array.from(box.querySelectorAll('img')).filter((img) => (img.naturalWidth || img.width || 0) > 40).length;
    posts.push({ post_url: href, text: text, author_id: '', image_count: images, card_id: markCard(box) });
  }
  for (const message of document.querySelectorAll('[data-ad-rendering-role="story_message"]')) {
    let node = message;
    let href = '';
    for (let i = 0; i < 18 && node && !href; i += 1) {
      const anchors = node.querySelectorAll ? node.querySelectorAll('a[href]') : [];
      for (const anchor of anchors) {
        const raw = anchor.href || '';
        const postsAt = raw.indexOf('/posts/');
        const permaAt = raw.indexOf('/permalink/');
        const gmAt = raw.indexOf('set=gm.');
        const pcbAt = raw.indexOf('set=pcb.');
        let postId = '';
        if (postsAt >= 0) postId = raw.slice(postsAt + 7).split(/[/?#]/)[0];
        else if (permaAt >= 0) postId = raw.slice(permaAt + 11).split(/[/?#]/)[0];
        else if (gmAt >= 0) postId = raw.slice(gmAt + 7).split('&')[0];
        else if (pcbAt >= 0) postId = raw.slice(pcbAt + 8).split('&')[0];
        if (!postId || !groupSlug) continue;
        href = 'https://www.facebook.com/groups/' + groupSlug + '/posts/' + decodeURIComponent(postId);
        break;
      }
      if (!href) {
        const plain = Array.from(anchors).find((anchor) => {
          const raw = anchor.href || '';
          return raw.includes('/groups/' + groupSlug) && !raw.includes('/user/') && raw.includes('__cft__');
        });
        if (plain) href = plain.href;
      }
      node = node.parentElement;
    }
    if (!href || seen.has(href)) continue;
    const text = (message.innerText || '').trim().slice(0, 2000);
    if (text.length < 2) continue;
    seen.add(href);
    message.setAttribute('data-fb-post', href);
    // card phải là article chứa story, không phải node cao (dễ lấn sang bài khác)
    const articleHost = message.closest('[role="article"]') || node || message;
    posts.push({ post_url: href, text: text, author_id: '', image_count: 0, card_id: markCard(articleHost) });
  }
  return posts;
}
"""
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


class ChromeSession:
    def __init__(self, headless, proxy, user_data_dir=None):
        self.headless = headless
        self.proxy = proxy
        self.user_data_dir = user_data_dir
        self._playwright = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        options = {"channel": "chrome", "headless": self.headless}
        if self.proxy:
            options["proxy"] = self.proxy
        if self.user_data_dir:
            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            return await self._playwright.chromium.launch_persistent_context(
                self.user_data_dir, **options
            )
        return await self._playwright.chromium.launch(**options)

    async def __aexit__(self, exc_type, exc, tb):
        if self._playwright:
            await self._playwright.stop()


class FacebookFanpageCommenter:
    def __init__(self, urls, cookies_file, comment_file, page_id, access_token=None, proxy=None, delay_min=1, delay_max=60, num_threads=3, headless=True, comment_mode="ui", require_proxy=True, user_data_dir=None, cookies_text=None, account_name=None):
        self.urls = self.parse_urls(urls)
        self.cookies_file = Path(cookies_file)
        self.cookies_text = cookies_text
        self.comment_file = Path(comment_file)
        self.page_id = str(page_id).strip() if page_id else ""
        self.proxy = proxy
        self.require_proxy = require_proxy
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.num_threads = num_threads
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.account_name = account_name or "cli"
        self.log = logging.LoggerAdapter(logger, {"account": self.account_name})
        self.comments = self.load_comments()
        self.page = self.context = self.browser = self._launcher = None
        self._page_ready = False
        self.last_comment_locked = False

    def parse_urls(self, urls_str):
        if not urls_str:
            return []
        return [url.strip() for url in urls_str.split(",") if url.strip()]

    def load_comments(self):
        if not self.comment_file.exists():
            raise FileNotFoundError(f"File comment_list.txt không tồn tại: {self.comment_file}")
        with open(self.comment_file, "r", encoding="utf-8") as f:
            comments = [line.strip() for line in f if line.strip()]
        self.log.info(f"Đã tải {len(comments)} comment")
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
        self.log.info(f"Đã tải {len(post_ids)} Post ID")
        return post_ids

    def load_browser_cookies(self):
        if self.cookies_text is not None:
            raw = self.cookies_text.strip()
            if not raw:
                raise ValueError("Cookie trống")
        else:
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

    def ensure_proxy(self):
        if self.proxy:
            return self.proxy
        proxy_path = Path(__file__).resolve().parents[2] / "account" / "proxy.txt"
        if proxy_path.is_file():
            self.proxy = next(
                (line.strip() for line in proxy_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()),
                "",
            )
        if not self.proxy:
            raise RuntimeError("Không có proxy để gắn vào trình duyệt. Điền account/proxy.txt")
        return self.proxy

    def proxy_config(self):
        self.ensure_proxy()
        parsed = urlsplit(self.proxy)
        if not parsed.hostname:
            return {"server": self.proxy}
        port = f":{parsed.port}" if parsed.port else ""
        config = {"server": f"{parsed.scheme}://{parsed.hostname}{port}"}
        if parsed.username:
            config["username"] = parsed.username
            config["password"] = parsed.password or ""
        return config

    def _chrome_launcher(self):
        proxy = self.proxy_config() if self.require_proxy else None
        return ChromeSession(
            headless=bool(self.headless),
            proxy=proxy,
            user_data_dir=self.user_data_dir,
        )

    async def login_with_cookie(self):
        self.log.info("Đang login bằng cookie (Chrome)...")
        self._launcher = self._chrome_launcher()
        try:
            launched = await self._launcher.__aenter__()
            if self.user_data_dir:
                # persistent context: the returned object IS the context
                self.browser = None
                context = launched
            else:
                self.browser = launched
                context = await self.browser.new_context()
            self.context = context
            await context.add_cookies(self.load_browser_cookies())
            # persistent context restore lại các tab phiên trước (có thể đang ở
            # group/post cũ) → đóng hết, chỉ giữ tab mới của phiên này.
            if self.user_data_dir:
                for old_page in context.pages:
                    try:
                        await old_page.close()
                    except Exception:
                        pass
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
            self.log.info("Đã mở Facebook")
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
                self.log.debug("Context cleanup failed: %s", type(error).__name__)
        if launcher:
            try:
                await launcher.__aexit__(None, None, None)
            except BaseException as error:
                self.log.debug("InvisiblePlaywright cleanup failed: %s", type(error).__name__)

    async def _switch_to_page(self):
        if not re.fullmatch(r"[0-9]+", self.page_id or ""):
            raise ValueError("Facebook Page ID không hợp lệ; phải là chuỗi số ASCII")
        # Nếu đã switch thành công trước đó thì không cần lặp lại toàn bộ quy
        # trình (nút 'Chuyển ngay' sẽ biến mất sau khi đã ở danh tính Page).
        if self._page_ready:
            return
        await self.page.goto(
            f"https://www.facebook.com/{self.page_id}",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        # Nút switch tới Page có 2 layout khác nhau:
        #   classic → button/link "Chuyển ngay" | "Switch now" (nằm trên trang Page)
        #   New Pages Experience → vào "Quản lý trang" rồi mở profile switcher góc phải
        switch_now = self.page.locator(
            "button, [role='button'], [role='link'], a"
        ).filter(
            has_text=re.compile(
                r"^Chuyển ngay$|^Switch now$",
                re.I,
            )
        )
        # chờ nút 'Chuyển ngay' tối đa ~10s
        for _ in range(10):
            if await switch_now.count():
                break
            await self.page.wait_for_timeout(1000)
        if await switch_now.count():
            await switch_now.first.click()
            for _ in range(20):
                if not await switch_now.count():
                    break
                await self.page.wait_for_timeout(500)
            else:
                raise RuntimeError("Không xác nhận được danh tính Page")
            self._page_ready = True
            self.log.info("Đã chuyển sang danh tính Page %s", self.page_id)
            return

        # NPE layout: không có nút 'Chuyển ngay'. Nếu đang ở 'Quản lý trang' thì
        # đã là danh tính Page → xong. Còn không thì mở menu avatar góc phải
        # và chọn Page trong menu switcher.
        try:
            on_manager = await self.page.evaluate(
                """() => (document.body.innerText || '').includes('Quản lý trang')
                        || (document.body.innerText || '').includes('Page management')"""
            )
        except Exception:
            on_manager = False
        if on_manager:
            self._page_ready = True
            self.log.info("Đã ở Quản lý trang — coi như danh tính Page %s", self.page_id)
            return

        if await self._switch_via_avatar_menu():
            self._page_ready = True
            self.log.info("Đã chuyển sang Page qua menu avatar %s", self.page_id)
            return

        # Fallback: kiểm tra composer đã hiển thị đúng Page chưa
        if await self._already_on_page():
            self._page_ready = True
            self.log.info("Đã ở danh tính Page (composer xác nhận)")
            return

        try:
            dbg = Path(__file__).resolve().parent / "data" / "debug"
            dbg.mkdir(parents=True, exist_ok=True)
            await self.page.screenshot(path=str(dbg / f"no-switch-{self.account_name}.png"))
        except Exception:
            pass
        raise RuntimeError("Không thấy nút chuyển sang Page (đã thử cả menu avatar)")

    async def _switch_via_avatar_menu(self):
        """Mở menu avatar góc phải và chọn Page trong switcher (NPE layout)."""
        try:
            # nút tròn có avatar hình ảnh user ở header phải, cuối cụm icon
            avatar = self.page.locator(
                "div[role='navigation'] a[aria-label*='Trang cá nhân'], "
                "div[role='navigation'] a[aria-label*='profile' i], "
                "div[role='navigation'] [role='button'][aria-haspopup='menu'], "
                "a[aria-label*='Tài khoản'], a[aria-label*='Account' i]"
            )
            if not await avatar.count():
                return False
            await avatar.last.click()
            await self.page.wait_for_timeout(1500)
            # menu hiện lên — chọn mục có tên Page (hoặc 'Chuyển sang' / 'Switch to')
            option = self.page.locator(
                "[role='menu'] [role='menuitem'], [role='menu'] a, "
                "[role='dialog'] [role='button'], [role='menu'] [role='button']"
            ).filter(
                has_text=re.compile(
                    rf"Chuyển sang|Switch to|{re.escape(self.page_id)}|Trang",
                    re.I,
                )
            )
            if not await option.count():
                # bất kỳ mục nào trong menu là link tới /{page_id}
                option = self.page.locator(
                    f"[role='menu'] a[href*='{self.page_id}'], "
                    f"[role='dialog'] a[href*='{self.page_id}']"
                )
            if not await option.count():
                await self.page.keyboard.press("Escape")
                return False
            await option.first.click()
            await self.page.wait_for_timeout(3000)
            return True
        except Exception:
            return False

    async def _already_on_page(self):
        """Chỉ trả True khi CHẮC đã ở danh tính Page: composer comment trên trang Page
        hiển thị chip 'Bình luận với tư cách' có link tới page_id. Các heuristic khác
        (URL, menu avatar) không đủ tin — trả False để nút switch xử lý."""
        try:
            composer = self.page.locator(
                "[contenteditable='true'][aria-label*='Bình luận'], "
                "[contenteditable='true'][aria-label*='comment' i]"
            ).first
            if not await composer.count():
                return False
            await composer.click()
            await self.page.wait_for_timeout(800)
            # chip actor trong composer — khi đã switch là link tới trang Page
            acting = await self.page.locator(
                f"a[href*='/{self.page_id}'], [role='combobox'] >> text=/./"
            ).count()
            await self.page.keyboard.press("Escape")
            return bool(acting)
        except Exception:
            return False

    async def _set_comment_text(self, composer, comment_text):
        """Focus the box in the page and type once. Playwright click waits 30s and stalls the run."""
        await composer.evaluate(
            """(el) => {
                el.scrollIntoView({block: 'center', inline: 'nearest'});
                el.focus();
                el.click();
            }"""
        )
        await self.page.keyboard.insert_text(comment_text)
        await self.page.wait_for_timeout(300)
        written = " ".join((await composer.inner_text()).split())
        if written.count(comment_text) != 1:
            raise RuntimeError("Ô comment không nhận nội dung")

    async def _post_comment_ui(self, post_id, comment_text):
        if not self.page:
            self.log.warning("Bỏ qua comment: thiếu phiên Facebook")
            return False
        try:
            target = self.ui_target_url(post_id)
            await self._switch_to_page()
            await self.page.goto(target, wait_until="domcontentloaded", timeout=60000)
            composer = self.page.locator(
                '[contenteditable="true"][aria-label*="Bình luận"], '
                '[contenteditable="true"][aria-label*="comment" i]'
            ).locator("visible=true").first
            try:
                await composer.wait_for(state="visible", timeout=8000)
            except Exception:
                self.last_comment_locked = await self._comments_locked()
                if self.last_comment_locked:
                    self.log.warning("Bài đã khóa comment")
                else:
                    self.log.warning("Không thấy ô comment trên bài viết")
                return False
            await composer.scroll_into_view_if_needed()
            await self._set_comment_text(composer, comment_text)
            await composer.press("Enter")
            posted = self.page.get_by_text(comment_text, exact=True)
            if not await posted.count():
                self.log.warning("Không xác nhận được comment đã hiện trên bài")
                return False
            self.log.info("Comment UI thành công")
            return True
        except (ValueError, RuntimeError) as error:
            self.log.warning("Comment UI không thực hiện được: %s", error)
            return False

    async def _comments_locked(self):
        body = " ".join((await self.page.locator("body").inner_text()).split()).lower()
        phrases = (
            "bình luận bị tắt",
            "đã tắt bình luận",
            "tắt tính năng bình luận",
            "commenting is turned off",
            "comments are turned off",
        )
        return any(phrase in body for phrase in phrases)

    async def expand_see_more(self):
        if not self.page:
            return 0
        return await self.page.evaluate(
            """() => {
                let clicks = 0;
                for (const el of document.querySelectorAll('[role="button"]')) {
                    const text = (el.innerText || '').trim();
                    if (text === 'Xem thêm' || text === 'See more') {
                        el.click();
                        clicks += 1;
                    }
                }
                return clicks;
            }"""
        )

    def _dialog_composer(self):
        """Comment box Facebook opens in the post popup, outside the feed card."""
        return self.page.locator(
            '[role="dialog"] [contenteditable="true"][aria-label*="Bình luận" i], '
            '[role="dialog"] [contenteditable="true"][aria-label*="comment" i], '
            '[role="dialog"] [role="textbox"][aria-label*="Bình luận" i], '
            '[role="dialog"] [role="textbox"][aria-label*="comment" i]'
        ).locator("visible=true")

    async def _close_post_dialog(self):
        """Close only the post popup. Leave the group feed in place."""
        try:
            closed = await self.page.evaluate(
                """() => {
                    const dialog = document.querySelector('[role="dialog"]');
                    if (!dialog) return false;
                    const button = Array.from(dialog.querySelectorAll('[aria-label]')).find((el) =>
                        /^(đóng|close)$/i.test((el.getAttribute('aria-label') || '').trim())
                    );
                    if (!button) return false;
                    button.click();
                    return true;
                }"""
            )
            if closed:
                await self.page.wait_for_timeout(800)
            still_open = await self.page.locator('[role="dialog"]').count()
            on_permalink = "/permalink/" in (self.page.url or "")
            if still_open and on_permalink:
                await self.page.go_back(wait_until="domcontentloaded", timeout=15000)
                await self.page.wait_for_timeout(800)
        except Exception:
            return

    async def comment_on_card(self, card_id, comment_text):
        """Comment in the feed card that is already on screen."""
        self.last_comment_locked = False
        if not self.page or not card_id:
            return False
        card = self.page.locator(f'[data-fb-card="{card_id}"]').first
        try:
            await card.wait_for(state="attached", timeout=5000)
        except Exception:
            self.log.warning("Không còn thấy khung bài trên màn hình")
            return False
        composer = card.locator(
            '[contenteditable="true"][aria-label*="Bình luận" i], '
            '[contenteditable="true"][aria-label*="comment" i], '
            '[role="textbox"][aria-label*="Bình luận" i], '
            '[role="textbox"][aria-label*="comment" i]'
        ).locator("visible=true")
        # Nút Bình luận trên group thường chỉ là icon, không có SVG và không có chữ.
        # Bấm lần lượt: nhãn Bình luận, rồi nút ngay bên phải Thích, rồi số bình luận.
        dialog = self._dialog_composer()
        for attempt in range(4):
            if await composer.count() or await dialog.count():
                break
            opened = await card.evaluate(
                """(el, attempt) => {
                    const visible = (node) => {
                        const r = node.getBoundingClientRect();
                        return r.width > 20 && r.height > 14 && r.width < 360 && r.bottom > 0;
                    };
                    const targets = [];
                    const seen = new Set();
                    const add = (node) => {
                        if (!node || seen.has(node) || !visible(node)) return;
                        if (node.closest('[contenteditable="true"], [role="textbox"]')) return;
                        seen.add(node);
                        targets.push(node);
                    };
                    for (const node of el.querySelectorAll('[aria-label], [role="button"], [role="link"]')) {
                        const label = ((node.getAttribute('aria-label') || '') + ' ' + (node.innerText || ''))
                            .replace(/\\s+/g, ' ').trim().toLowerCase();
                        if (!label || label.length > 60) continue;
                        if (/xem thêm|see more|phản hồi|reply|chia sẻ|share/.test(label)) continue;
                        if (/bình luận|comment/.test(label)) add(node);
                    }
                    const likeRe = /^(thích|like)$/i;
                    let likeBtn = null;
                    for (const node of el.querySelectorAll('[role="button"], [tabindex="0"]')) {
                        const aria = (node.getAttribute('aria-label') || '').trim();
                        const text = (node.innerText || '').trim();
                        if (likeRe.test(aria) || likeRe.test(text)) { likeBtn = node; break; }
                    }
                    if (likeBtn) {
                        const likeBox = likeBtn.getBoundingClientRect();
                        const mid = likeBox.top + likeBox.height / 2;
                        const row = Array.from(el.querySelectorAll('[role="button"], [tabindex="0"]')).filter((node) => {
                            if (node === likeBtn || !visible(node)) return false;
                            const box = node.getBoundingClientRect();
                            const center = box.top + box.height / 2;
                            return Math.abs(center - mid) < 26 && box.left >= likeBox.left - 4;
                        });
                        row.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                        const beside = row.find((node) => node.getBoundingClientRect().left > likeBox.right - 10);
                        if (beside) add(beside);
                    }
                    const target = targets[attempt];
                    if (!target) return 'no-comment-btn';
                    target.scrollIntoView({block: 'center'});
                    target.click();
                    return 'clicked';
                }""",
                attempt,
            )
            if opened != "clicked":
                break
            try:
                await dialog.first.wait_for(state="visible", timeout=1500)
            except Exception:
                try:
                    await composer.first.wait_for(state="visible", timeout=1000)
                except Exception:
                    await self.page.wait_for_timeout(400)
        in_dialog = await dialog.count()
        box = dialog if in_dialog else composer
        if not await box.count():
            self.log.warning("Không thấy ô comment trong khung bài")
            await self._close_post_dialog()
            return False
        try:
            await self._set_comment_text(box.first, comment_text)
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(800)
            scope = self.page.locator('[role="dialog"]') if in_dialog else card
            posted = scope.get_by_text(comment_text, exact=True)
            if not await posted.count():
                self.log.warning("Không xác nhận được comment đã hiện trong khung bài")
                if in_dialog:
                    await self._close_post_dialog()
                return False
            self.log.info("Đã comment ngay trên bài đang hiện")
            if in_dialog:
                await self._close_post_dialog()
            return True
        except Exception as error:
            self.log.warning("Comment ngay trên bài không thực hiện được: %s", type(error).__name__)
            await self._close_post_dialog()
            return False

    async def post_comment(self, post_id, comment_text):
        self.last_comment_locked = False
        return await self._post_comment_ui(post_id, comment_text)

    async def comment_random(self):
        post_ids = self.urls or self.load_uids()

        if not self.comments:
            self.log.warning("Không có comment nào")
            return
        if not post_ids:
            self.log.warning("Không có Post ID nào")
            return

        pool = list(dict.fromkeys(self.comments))
        for index, post_id in enumerate(post_ids):
            if not pool:
                self.log.warning("Hết comment chưa dùng")
                return
            comment = random.choice(pool)
            pool.remove(comment)
            try:
                target = self.ui_target_url(post_id)
            except ValueError as error:
                self.log.warning("Bỏ qua target không hợp lệ: %s", error)
                continue
            self.log.info("Đang comment trên %s", target)
            success = await self.post_comment(post_id, comment)
            if not success:
                self.log.warning("Comment không hiện trên %s", post_id)
                continue
            self.comments.remove(comment)
            if index == len(post_ids) - 1 or self.delay_max <= 0:
                continue
            delay = random.randint(self.delay_min * 60, self.delay_max * 60)
            self.log.info("Đang delay %s phút...", delay // 60)
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                self.log.info("Stopped by user")
                raise

    async def comment_posts(self, jobs, cooldown_seconds=0):
        """Comment each job in order. Several feed links can open the same post."""
        commented_posts = set()
        for index, job in enumerate(jobs):
            try:
                target = self.ui_target_url(job.post_url)
            except ValueError as error:
                self.log.warning("Bỏ qua target không hợp lệ: %s", error)
                job.success = False
                continue
            await self.page.goto(target, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_timeout(1000)
            match = re.search(r"/(?:posts|permalink)/([^/?#]+)", self.page.url)
            post_key = match.group(1) if match else ""
            if post_key and post_key in commented_posts:
                self.log.info("Bỏ qua, link này mở lại bài đã comment: %s", post_key)
                job.success = False
                job.duplicate = True
                continue
            if post_key:
                job.post_url = self.page.url.split("?")[0]
            self.log.info("Đang comment trên %s", job.post_url)
            job.success = await self.post_comment(job.post_url, job.comment)
            job.locked = self.last_comment_locked
            if post_key and job.success:
                commented_posts.add(post_key)
            if not job.success:
                self.log.warning("Comment không hiện trên %s", job.post_url)
                continue
            if cooldown_seconds > 0 and index < len(jobs) - 1:
                self.log.info("Nghỉ %s giây", cooldown_seconds)
                await asyncio.sleep(cooldown_seconds)
        return jobs

    async def collect_group_posts(self):
        if not self.page:
            raise RuntimeError("Chưa có phiên Facebook để quét group")
        return await self.page.evaluate(_GROUP_POST_SCRIPT)

    async def run(self):
        try:
            await self.login_with_cookie()
            await self.comment_random()
        finally:
            await self.close_browser()
            self.log.info("Finished")
