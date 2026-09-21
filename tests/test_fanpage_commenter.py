import pytest
import facebook_fanpage_commenter as commenter_module
from facebook_fanpage_commenter import FacebookFanpageCommenter


def make_commenter(tmp_path, page_id="1234567890"):
    comments = tmp_path / "comments.txt"
    comments.write_text("hello\n", encoding="utf-8")
    return FacebookFanpageCommenter(
        urls="",
        cookies_file=tmp_path / "cookies.txt",
        comment_file=comments,
        page_id=page_id,
    )


@pytest.mark.asyncio
async def test_login_navigates_and_cleans_up(monkeypatch, tmp_path):
    events = []

    class FakePage:
        url = "about:blank"

        async def goto(self, url, **kwargs):
            events.append("goto")
            self.url = url

        async def wait_for_timeout(self, _):
            pass

        def locator(self, _):
            return self

        async def count(self):
            return 0

    class FakeContext:
        async def add_cookies(self, cookies):
            assert cookies

        async def new_page(self):
            return FakePage()

        async def close(self):
            events.append("context")

    class FakeBrowser:
        async def new_context(self):
            return FakeContext()

        async def close(self):
            events.append("browser")

    class FakeChromium:
        async def launch(self, **kwargs):
            return FakeBrowser()

    class FakeLauncher:
        def __init__(self, **kwargs):
            events.append(("launch", kwargs.get("headless"), kwargs.get("proxy")))

        async def __aenter__(self):
            return FakeBrowser()

        async def __aexit__(self, *args):
            events.append("playwright")

    monkeypatch.setattr(commenter_module, "InvisiblePlaywright", FakeLauncher)
    cookies = tmp_path / "cookies.txt"
    comments = tmp_path / "comments.txt"
    cookies.write_text("c_user=example; xs=session", encoding="utf-8")
    comments.write_text("hello\n", encoding="utf-8")
    commenter = FacebookFanpageCommenter("123_456", cookies, comments, "123", proxy="http://127.0.0.1:8080")
    page_context = await commenter.login_with_cookie()
    assert commenter.page.url == "https://www.facebook.com/"
    assert page_context is commenter.context
    await commenter.close_browser()
    assert events[0][0] == "launch"
    assert events[0][2]["server"] == "http://127.0.0.1:8080"
    assert "goto" in events
    assert events[-1] == "playwright"

@pytest.mark.asyncio
async def test_random_comment(tmp_path):
    comments = tmp_path / "comments.txt"
    comments.write_text("xin chao\n", encoding="utf-8")
    commenter = FacebookFanpageCommenter(
        urls="1234567890",
        cookies_file=tmp_path / "cookies.txt",
        comment_file=comments,
        page_id="1234567890"
    )
    assert len(commenter.comments) > 0
    assert commenter.comments[0] != ""


@pytest.mark.asyncio
async def test_comment_failure_does_not_retry(tmp_path):
    commenter = make_commenter(tmp_path, page_id="123")
    commenter.urls = ["123_456"]
    commenter.page = object()
    calls = []

    async def fail_once(post_id, comment):
        calls.append((post_id, comment))
        return False

    commenter.post_comment = fail_once
    await commenter.comment_random()
    assert len(calls) == 1


def test_normalize_post_id_from_url(tmp_path):
    commenter = make_commenter(tmp_path, page_id="123")
    assert commenter.normalize_post_id(
        "https://www.facebook.com/123/posts/456"
    ) == "123_456"
    assert commenter.normalize_post_id(
        "https://www.facebook.com/permalink.php?story_fbid=456&id=123"
    ) == "123_456"
    with pytest.raises(ValueError, match="không thuộc Page"):
        commenter.normalize_post_id("https://www.facebook.com/999/posts/456")


class ScriptedLocator:
    def __init__(self, page, kind):
        self.page = page
        self.kind = kind

    @property
    def first(self):
        return self

    async def count(self):
        return self.page.counts.get(self.kind, 0)

    async def click(self):
        self.page.events.append(f"click:{self.kind}")
        if self.kind == "switch":
            self.page.counts["identity"] = 1
            self.page.counts["switch"] = 0

    async def fill(self, text):
        self.page.events.append(f"fill:{text}")
        self.page.filled = text

    async def evaluate(self, script, arg=None):
        self.page.events.append(f"write:{arg}")
        doubled = f"{arg}{arg}" if arg else ""
        self.page.filled = doubled if self.page.double_write else arg

    async def inner_text(self):
        return self.page.filled

    async def press(self, key):
        self.page.events.append(f"press:{key}")

    def filter(self, has_text=None):
        return ScriptedLocator(self.page, "switch")

    async def wait_for(self, **kwargs):
        if not await self.count():
            raise RuntimeError("missing")

    async def scroll_into_view_if_needed(self):
        return None


class ScriptedPage:
    def __init__(self):
        self.url = "https://www.facebook.com/"
        self.events = []
        self.filled = ""
        self.double_write = False
        self.counts = {"identity": 0, "switch": 1, "box": 1, "submit": 1, "posted": 1}

    async def wait_for_timeout(self, _ms):
        return None

    async def goto(self, url, **kwargs):
        self.events.append(f"goto:{url}")
        self.url = url

    def locator(self, selector):
        return ScriptedLocator(self, "box")

    def get_by_text(self, pattern, exact=False):
        if exact:
            kind = "posted" if self.filled and pattern == self.filled else "missing"
            return ScriptedLocator(self, kind)
        return ScriptedLocator(self, "identity")

    def get_by_role(self, role, name=None):
        label = getattr(name, "pattern", "")
        if "Switch" in label or "Chuy" in label:
            return ScriptedLocator(self, "switch")
        return ScriptedLocator(self, "submit")


@pytest.mark.asyncio
async def test_ui_mode_submits_visible_comment(tmp_path):
    commenter = make_commenter(tmp_path, page_id="123")
    commenter.comment_mode = "ui"
    commenter.page = ScriptedPage()
    assert await commenter.post_comment("123_456", "xin chao") is True
    assert "goto:https://www.facebook.com/123/posts/456" in commenter.page.events
    assert "write:xin chao" in commenter.page.events


@pytest.mark.asyncio
async def test_ui_mode_does_not_submit_doubled_text(tmp_path):
    commenter = make_commenter(tmp_path, page_id="123")
    page = ScriptedPage()
    page.double_write = True
    commenter.page = page
    assert await commenter.post_comment("123_456", "xin chao") is False
    assert not any(event.startswith("click:submit") for event in page.events)


@pytest.mark.asyncio
async def test_ui_mode_fails_without_page_switch(tmp_path):
    commenter = make_commenter(tmp_path, page_id="123")
    commenter.comment_mode = "ui"
    page = ScriptedPage()
    page.counts["switch"] = 0
    page.goto = _goto_without_identity(page)
    commenter.page = page
    assert await commenter.post_comment("123_456", "xin chao") is False


def _goto_without_identity(page):
    async def goto(url, **kwargs):
        page.events.append(f"goto:{url}")
        page.url = url

    return goto


def test_proxy_config_splits_credentials(tmp_path):
    commenter = make_commenter(tmp_path)
    commenter.proxy = "http://user:pass@proxy.example:8080"
    assert commenter.proxy_config() == {
        "server": "http://proxy.example:8080",
        "username": "user",
        "password": "pass",
    }
