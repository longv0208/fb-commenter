"""Request payload validation (KISS: plain dicts + ValueError)."""
import re

_NAME_RE = re.compile(r"^[\w\- ]{1,64}$", re.U)


def account_from_payload(data, partial=False):
    if not isinstance(data, dict):
        raise ValueError("Payload phải là JSON object")
    acc = {}
    name = str(data.get("name", "")).strip()
    if not partial or name:
        if not _NAME_RE.match(name):
            raise ValueError("Tên account không hợp lệ (1-64 ký tự, chữ/số/-/_)")
        acc["name"] = name
    for field in ("cookie", "page_id", "proxy", "profile_dir", "comment_list"):
        if field in data or not partial:
            acc[field] = str(data.get(field, "")).strip()
    if "page_id" in acc and acc["page_id"] and not acc["page_id"].isdigit():
        raise ValueError("page_id phải là chuỗi số")
    if "proxy" in acc and acc["proxy"]:
        proxy = acc["proxy"]
        if not re.match(r"^(https?|socks5?)://", proxy):
            raise ValueError("proxy phải dạng http:// hoặc socks5://")
    acc["use_profile"] = bool(data.get("use_profile", False))
    return acc


def run_from_payload(data):
    if not isinstance(data, dict):
        raise ValueError("Payload phải là JSON object")
    mode = data.get("mode", "uid")
    if mode not in ("uid", "campaign"):
        raise ValueError("mode phải là 'uid' hoặc 'campaign'")
    opts = {
        "mode": mode,
        "campaign": str(data.get("campaign", "")).strip(),
        "urls": str(data.get("urls", "")).strip(),
        "delay_min": int(data.get("delay_min", 1)),
        "delay_max": int(data.get("delay_max", 60)),
        "cooldown": data.get("cooldown"),
        "headless": bool(data.get("headless", False)),
        "dry_run": bool(data.get("dry_run", False)),
        "no_proxy": bool(data.get("no_proxy", False)),
    }
    if mode == "campaign" and not opts["campaign"]:
        raise ValueError("Thiếu tên campaign")
    if opts["delay_min"] > opts["delay_max"]:
        raise ValueError("delay_min phải <= delay_max")
    return opts
