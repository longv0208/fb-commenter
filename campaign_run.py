import json
import logging
import random
import re
from pathlib import Path

from campaign_store import already_commented, connect, save_comment, save_post
from comment_job import CommentJob
from jev_client import JevError, review_post
from post_rules import HELP_PHRASES, hidden_author_ids, keyword_match

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


async def select_newest_posts(page):
    """Group feed opens on Recent activity. Open that menu and choose newest posts."""
    opened = False
    for _ in range(15):
        opened = await page.evaluate(
            """() => {
                const button = document.querySelector(
                    "[role='button'][aria-label*='sắp xếp bảng feed'], [role='button'][aria-label*='Sort group feed']"
                );
                if (!button) return false;
                button.click();
                return true;
            }"""
        )
        if opened:
            break
        await page.wait_for_timeout(400)
    if not opened:
        trigger = page.get_by_text("Hoạt động mới đây", exact=True)
        if not await trigger.count():
            trigger = page.get_by_text("Recent activity", exact=True)
        if not await trigger.count():
            raise RuntimeError("Không thấy bộ lọc Hoạt động mới đây")
        await trigger.first.click()
    await page.wait_for_timeout(400)
    choice = page.get_by_text("Bài viết mới", exact=True)
    if not await choice.count():
        choice = page.get_by_text("New posts", exact=True)
    if not await choice.count():
        choice = page.locator("[role='menuitem'], [role='option'], [role='button'], [role='radio']").filter(
            has_text=_NEWEST_HINT
        )
    if not await choice.count():
        raise RuntimeError("Không thấy lựa chọn Bài viết mới")
    await choice.first.click()
    await page.wait_for_timeout(700)
    logger.info("Đã chọn lọc Bài viết mới")


async def scan_group(commenter, group_url, campaign):
    await commenter.page.goto(group_url, wait_until="domcontentloaded", timeout=60000)
    await select_newest_posts(commenter.page)
    found = {}
    empty_rounds = 0
    for _ in range(int(campaign["max_scrolls"])):
        batch = await commenter.collect_group_posts()
        added = 0
        for item in batch:
            url = (item.get("post_url") or "").split("?")[0]
            if not url or url in found:
                continue
            item["post_url"] = url
            item["group_url"] = group_url
            found[url] = item
            added += 1
        if added == 0:
            empty_rounds += 1
            if empty_rounds >= int(campaign["empty_scroll_limit"]):
                break
        else:
            empty_rounds = 0
        await commenter.page.mouse.wheel(0, int(campaign["scroll_pixels"]))
        await commenter.page.wait_for_timeout(int(campaign["scroll_pause_ms"]))
    return list(found.values())


def select_posts(posts, campaign, hidden_ids, page_id, db):
    selected = []
    hidden_count = 0
    for post in posts:
        author = str(post.get("author_id") or "")
        if author and (author in hidden_ids or author == str(page_id)):
            hidden_count += 1
            save_post(db, post, "hidden")
            continue
        if already_commented(db, post["post_url"]):
            if keyword_match(post.get("text", ""), campaign["subjects"], campaign["help_phrases"]):
                logger.info("Khớp từ khóa nhưng đã comment: %s", post["post_url"])
            save_post(db, post, "commented")
            continue
        matched = keyword_match(post.get("text", ""), campaign["subjects"], campaign["help_phrases"])
        if not matched and not campaign["jev_review_all"]:
            save_post(db, post, "filtered")
            continue
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


async def run_campaign(commenter, parent_dir, name, dry_run):
    campaign = load_campaign(parent_dir, name)
    hidden = hidden_author_ids(Path(parent_dir) / "account" / "hidden-authors.txt")
    db = connect(Path(__file__).resolve().parent / "data" / "app.db")
    await commenter.login_with_cookie()
    try:
        await commenter._switch_to_page()
        logger.info("Đã chuyển sang Page %s", commenter.page_id)
        scanned = []
        for group_url in campaign["groups"]:
            try:
                scanned.extend(await scan_group(commenter, group_url, campaign))
            except Exception as error:
                logger.warning("Bỏ qua group %s: %s", group_url, error)
        candidates, hidden_count = select_posts(
            scanned, campaign, hidden, commenter.page_id, db
        )
        if dry_run:
            logger.info(
                "Dry-run: quét %s, ẩn %s, chờ Jev %s. Không gửi comment.",
                len(scanned),
                hidden_count,
                len(candidates),
            )
            for post in candidates:
                preview = " ".join((post.get("text") or "").split())[:140]
                logger.info("Chờ duyệt %s | %s", post["post_url"], preview)
            return
        ready = apply_jev(candidates, campaign, db) if campaign["use_jev"] else candidates
        if not campaign["use_jev"]:
            logger.info("Bỏ qua Jev, comment %s bài khớp từ khóa", len(ready))
        pool = list(dict.fromkeys(commenter.comments))
        jobs = []
        per_group = {}
        for post in ready:
            if len(jobs) >= int(campaign["max_comments_per_run"]) or not pool:
                break
            group = post.get("group_url", "")
            if per_group.get(group, 0) >= int(campaign["max_comments_per_group"]):
                continue
            comment = random.choice(pool)
            pool.remove(comment)
            jobs.append(CommentJob(post["post_url"], comment, name))
            per_group[group] = per_group.get(group, 0) + 1
        await commenter.comment_posts(jobs, cooldown_seconds=int(campaign["cooldown_seconds"]))
        for job in jobs:
            save_comment(db, job.post_url, job.comment, job.success)
    finally:
        db.close()
        await commenter.close_browser()
