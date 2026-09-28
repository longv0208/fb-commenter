import json
import logging
import random
import re
from pathlib import Path

from campaign_store import already_commented, connect, post_status, save_comment, save_post, story_already_commented
from image_text import read_png
from comment_job import CommentJob
from jev_client import JevError, review_post
from post_rules import HELP_PHRASES, fold, hidden_author_ids, keyword_match

logger = logging.getLogger("fb_commenter")


def load_campaign(parent_dir, name):
    path = Path(parent_dir) / "account" / "campaigns" / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Không thấy campaign: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("groups"):
        raise ValueError(f"Campaign {name} chưa có group")
    data.setdefault("subjects", [])
    data.setdefault("help_phrases", list(HELP_PHRASES))
    data.setdefault("use_jev", False)
    data.setdefault("sort_newest", False)
    data.setdefault("max_scrolls", 30)
    data.setdefault("empty_scroll_limit", 4)
    data.setdefault("scroll_pixels", 700)
    data.setdefault("scroll_pause_ms", 4000)
    data.setdefault("max_comments_per_group", 5)
    data.setdefault("max_comments_per_run", 15)
    data.setdefault("cooldown_seconds", 120)
    data.setdefault("jev_confidence", 0.8)
    data.setdefault("jev_review_all", False)
    data["name"] = name
    return data


_SORT_TRIGGER = re.compile(
    r"^(Phù hợp nhất|Hoạt động mới đây|Bài viết mới|Most relevant|Recent activity|New posts)$",
    re.I,
)
_NEWEST_HINT = re.compile(
    r"Bài viết mới|Hiển thị bài viết gần đây đầu tiên|New posts|most recent posts first",
    re.I,
)


_SORT_LABELS = (
    "Phù hợp nhất",
    "Hoạt động mới đây",
    "Bài viết mới",
    "Most relevant",
    "Recent activity",
    "New posts",
)


async def select_newest_posts(page):
    """Open whichever feed sort is showing, then choose newest posts."""
    if page.is_closed():
        raise RuntimeError("Chrome đã đóng trước khi chọn Bài viết mới")
    trigger = page.locator(
        "[role='button'][aria-label*='sắp xếp bảng feed'], [role='button'][aria-label*='Sort group feed']"
    )
    label = ""
    if await trigger.count():
        label = ((await trigger.first.inner_text()) or (await trigger.first.get_attribute("aria-label") or "")).strip()
    else:
        for name in _SORT_LABELS:
            candidate = page.get_by_text(name, exact=True)
            if await candidate.count():
                trigger = candidate
                label = name
                break
    if not label:
        raise RuntimeError(
            "Không thấy bộ lọc feed. Cần một trong các nhãn: Phù hợp nhất, Hoạt động mới đây, Bài viết mới. "
            f"Trang: {page.url}"
        )
    logger.info("Bộ lọc feed đang hiện: %s", label.split("\n")[0][:80])
    if re.search(r"Bài viết mới|New posts", label, re.I):
        logger.info("Feed đã ở Bài viết mới")
        return
    await trigger.first.click()
    await page.wait_for_timeout(700)
    choice = page.get_by_text("Hiển thị bài viết gần đây đầu tiên", exact=True)
    if not await choice.count():
        choice = page.get_by_text("Bài viết mới", exact=True)
    if not await choice.count():
        choice = page.get_by_text("New posts", exact=True)
    if not await choice.count():
        choice = page.locator("[role='menuitem'], [role='option'], [role='button'], [role='radio']").filter(
            has_text=_NEWEST_HINT
        )
    if not await choice.count():
        visible = await page.evaluate(
            """() => Array.from(document.querySelectorAll('[role="menuitem"], [role="dialog"] [role="button"]'))
                .map((el) => (el.innerText || '').trim())
                .filter((text) => text && text.length < 80)
                .slice(0, 8)"""
        )
        raise RuntimeError(
            f"Không thấy lựa chọn Bài viết mới. Bộ lọc đang là {state['label']!r}. "
            f"Menu đang hiện: {visible}. Trang: {page.url}"
        )
    await choice.first.click()
    await page.wait_for_timeout(700)
    logger.info("Đã chọn lọc Bài viết mới")


async def read_post_images(page, post):
    text = post.get("text") or ""
    if not post.get("image_count"):
        return text
    locator = page.locator(f'[data-fb-post="{post["post_url"]}"] img')
    count = min(await locator.count(), 5)
    lines = [text] if text else []
    for index in range(count):
        try:
            png = await locator.nth(index).screenshot(timeout=3000)
        except Exception:
            continue
        found = await read_png(png)
        if found:
            lines.append(found)
    return "\n".join(lines)[:2000]


async def open_group(page, group_url):
    """Move from the Page screen to the group. A direct goto is often aborted after the Page switch."""
    await page.wait_for_timeout(2000)
    await page.evaluate("(url) => { window.location.assign(url); }", group_url)
    try:
        await page.wait_for_url("**/groups/**", timeout=30000)
    except Exception:
        current = page.url
        raise RuntimeError(f"Không vào được group, trang hiện tại là {current}") from None
    await page.wait_for_timeout(1500)
    for _ in range(10):
        if page.is_closed():
            raise RuntimeError("Chrome đã đóng sau khi vào group, trước khi chọn bộ lọc")
        ready = await page.evaluate(
            """() => {
                const text = document.body.innerText || '';
                return ['Phù hợp nhất', 'Hoạt động mới đây', 'Bài viết mới', 'Most relevant', 'Recent activity', 'New posts']
                    .some((label) => text.includes(label));
            }"""
        )
        if ready:
            return
        await page.wait_for_timeout(500)
    logger.info("Chưa thấy nhãn bộ lọc sau khi vào group %s", page.url)


def same_post(existing, item):
    """Photo links repeat with a stable /posts/ id. Text posts repeat with a new tracking link."""
    existing_id = re.search(r"/posts/([^/?#]+)", existing.get("post_url") or "")
    item_id = re.search(r"/posts/([^/?#]+)", item.get("post_url") or "")
    if existing_id and item_id and existing_id.group(1) == item_id.group(1):
        return True
    old = fold(existing.get("text") or "")[:200]
    new = fold(item.get("text") or "")[:200]
    return len(old) >= 30 and len(new) >= 30 and (old in new or new in old)


async def scan_group(commenter, group_url, campaign, db, pool, commented_total, dry_run, pause):
    """Scroll the feed and comment on a matching card before leaving it."""
    await open_group(commenter.page, group_url)
    await commenter.page.wait_for_timeout(3000)
    if campaign.get("sort_newest"):
        await select_newest_posts(commenter.page)
    seen = []
    group_comments = 0
    skipped_keyword = 0
    skipped_done = 0
    skipped_failed = 0
    empty_rounds = 0
    for _ in range(int(campaign["max_scrolls"])):
        if commented_total >= int(campaign["max_comments_per_run"]):
            logger.info("Đủ %s comment cho lượt này", campaign["max_comments_per_run"])
            break
        if group_comments >= int(campaign["max_comments_per_group"]):
            logger.info("Đủ %s comment cho group này", campaign["max_comments_per_group"])
            break
        await commenter.expand_see_more()
        await commenter.page.wait_for_timeout(400)
        batch = await commenter.collect_group_posts()
        logger.info("Màn này đọc được %s bài", len(batch))
        added = 0
        for item in batch:
            raw_url = item.get("post_url") or ""
            item["post_url"] = raw_url if "__cft__" in raw_url else raw_url.split("?")[0]
            item["group_url"] = group_url
            if not item["post_url"] or any(same_post(existing, item) for existing in seen):
                continue
            if not keyword_match(item.get("text", ""), campaign["subjects"], campaign["help_phrases"]):
                item["text"] = await read_post_images(commenter.page, item)
            seen.append(item)
            added += 1
            preview = " ".join((item.get("text") or "").split())[:120]
            if story_already_commented(db, item.get("text")) or already_commented(db, item["post_url"]):
                skipped_done += 1
                logger.info("Đã comment trước đó, bỏ qua | %s", preview)
                continue
            if not keyword_match(item.get("text", ""), campaign["subjects"], campaign.get("help_phrases")):
                skipped_keyword += 1
                logger.info("Không khớp | %s", preview)
                save_post(db, item, "filtered")
                continue
            logger.info("Khớp, comment ngay | %s", preview)
            if dry_run:
                continue
            if not pool or group_comments >= int(campaign["max_comments_per_group"]):
                break
            if commented_total >= int(campaign["max_comments_per_run"]):
                break
            comment = random.choice(pool)
            pool.remove(comment)
            ok = await commenter.comment_on_card(item.get("card_id"), comment)
            if not ok:
                skipped_failed += 1
                logger.warning("Không comment được bài đang hiện")
                continue
            group_comments += 1
            commented_total += 1
            save_post(db, item, "commented")
            save_comment(db, item["post_url"], comment, True)
            if pause > 0 and commented_total < int(campaign["max_comments_per_run"]):
                logger.info("Nghỉ %s giây", pause)
                await commenter.page.wait_for_timeout(int(pause) * 1000)
        if added == 0:
            empty_rounds += 1
            if empty_rounds >= int(campaign["empty_scroll_limit"]):
                break
        else:
            empty_rounds = 0
        ratio = float(campaign.get("scroll_ratio", 0.4))
        await commenter.page.evaluate(
            "(ratio) => window.scrollBy(0, Math.max(280, Math.round(window.innerHeight * ratio)))",
            ratio,
        )
        await commenter.page.wait_for_timeout(int(campaign["scroll_pause_ms"]))
    skipped = skipped_keyword + skipped_done + skipped_failed
    logger.info(
        "Tổng kết: đọc %s bài, comment %s, bỏ qua %s (không khớp %s, đã comment %s, không gửi được %s)",
        len(seen),
        group_comments,
        skipped,
        skipped_keyword,
        skipped_done,
        skipped_failed,
    )
    return commented_total


def select_posts(posts, campaign, hidden_ids, page_id, db):
    selected = []
    hidden_count = 0
    for post in posts:
        author = str(post.get("author_id") or "")
        preview = " ".join((post.get("text") or "").split())[:120]
        if post_status(db, post["post_url"]) == "comments_locked":
            logger.info("Bỏ qua bài khóa comment: %s", post["post_url"])
            continue
        if author and (author in hidden_ids or author == str(page_id)):
            hidden_count += 1
            save_post(db, post, "hidden")
            continue
        if story_already_commented(db, post.get("text")) or already_commented(db, post["post_url"]):
            phrases = campaign.get("help_phrases")
            if keyword_match(post.get("text", ""), campaign["subjects"], phrases):
                logger.info("Khớp từ khóa nhưng đã comment: %s", post["post_url"])
            save_post(db, post, "commented")
            continue
        matched = keyword_match(post.get("text", ""), campaign["subjects"], campaign.get("help_phrases"))
        if not matched and not campaign["jev_review_all"]:
            logger.info("Không khớp %s | %s", post["post_url"], preview)
            save_post(db, post, "filtered")
            continue
        logger.info("Khớp %s | %s", post["post_url"], preview)
        selected.append(post)
    return selected, hidden_count


def apply_jev(posts, campaign, db):
    ready = []
    for post in posts:
        try:
            label, confidence = review_post(post.get("text", ""), campaign["subjects"])
        except JevError as error:
            logger.warning("Jev bỏ qua bài: %s", error)
            save_post(db, post, "jev_failed")
            continue
        passed = label == "comment" and confidence >= float(campaign["jev_confidence"])
        save_post(db, post, "comment" if passed else "skip", label, confidence)
        if passed:
            ready.append(post)
    return ready


async def run_campaign(commenter, parent_dir, name, dry_run, cooldown_seconds=None):
    campaign = load_campaign(parent_dir, name)
    hidden = hidden_author_ids(Path(parent_dir) / "account" / "hidden-authors.txt")
    db = connect(Path(__file__).resolve().parent / "data" / "app.db")
    await commenter.login_with_cookie()
    try:
        await commenter._switch_to_page()
        logger.info("Đã chuyển sang Page %s", commenter.page_id)
        pool = list(dict.fromkeys(commenter.comments))
        pause = campaign["cooldown_seconds"] if cooldown_seconds is None else cooldown_seconds
        commented_total = 0
        for group_url in campaign["groups"]:
            try:
                commented_total = await scan_group(
                    commenter, group_url, campaign, db, pool, commented_total, dry_run, pause
                )
            except Exception:
                logger.exception("Dừng group %s", group_url)
        logger.info("Xong. Đã comment %s bài", commented_total)
    finally:
        db.close()
        await commenter.close_browser()
