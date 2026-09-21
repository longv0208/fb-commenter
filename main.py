import asyncio
import argparse
import logging
import re
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

from facebook_fanpage_commenter import FacebookFanpageCommenter

console = Console()


def sanitize_error_text(value, secret=""):
    text = str(value)
    if secret:
        text = text.replace(secret, "<redacted>")
    text = re.sub(
        r"(?i)(access_token|token|password|cookie)\s*[:=]\s*[\"']?[^\s,}\"']+",
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
    return re.sub(r"[\r\n]+", " ", text).strip()[:400]


async def main():
    parser = argparse.ArgumentParser(description="Facebook Fanpage Commenter CLI")
    parser.add_argument("--urls", help="List of post IDs or URLs separated by comma")
    parser.add_argument("--cookies", help="Path to cookies.txt file")
    parser.add_argument("--comment-list", help="Path to comment_list.txt file")
    parser.add_argument("--page-id", help="Facebook Page ID")
    parser.add_argument("--proxy", help="Proxy URL (e.g. http://user:pass@proxy-ip:port)")
    parser.add_argument("--delay-min", type=int, default=1, help="Minimum delay in minutes (default 1)")
    parser.add_argument("--delay-max", type=int, default=60, help="Maximum delay in minutes (default 60)")
    parser.add_argument("--threads", type=int, default=3, help="Number of concurrent threads")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Auto-detect files from parent folder
    base_dir = Path(__file__).resolve().parent
    parent_dir = base_dir.parents[1]

    if not args.urls:
        args.urls = ""

    if not args.cookies:
        cookies_path = parent_dir / "account" / "cookies.txt"
        if cookies_path.exists():
            args.cookies = str(cookies_path)
        else:
            account_list = parent_dir / "account" / "account list.txt"
            args.cookies = str(account_list if account_list.is_file() else base_dir / "cookies.txt")

    if not args.comment_list:
        comment_dir = parent_dir / "comments"
        for name in ("comment list.txt", "comment_list.txt"):
            comment_path = comment_dir / name
            if comment_path.exists():
                args.comment_list = str(comment_path)
                break
        else:
            args.comment_list = str(base_dir / "comment_list.txt")

    if not args.page_id:
        page_id_path = parent_dir / "account" / "page_id.txt"
        if page_id_path.exists():
            args.page_id = page_id_path.read_text(encoding="utf-8-sig").strip()
        else:
            page_txt = parent_dir / "account" / "page.txt"
            page_line = page_txt.read_text(encoding="utf-8-sig").strip() if page_txt.is_file() else ""
            args.page_id = page_line if page_line.isdigit() else ""

    if not args.proxy:
        proxy_path = parent_dir / "account" / "proxy.txt"
        if proxy_path.is_file():
            args.proxy = next(
                (line.strip() for line in proxy_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()),
                "",
            )

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console)]
    )

    console.print("[bold green]Starting Facebook Fanpage Commenter...[/bold green]")

    try:
        if not args.page_id:
            raise ValueError(
                "Cần Facebook Page ID số từ --page-id hoặc account/page_id.txt"
            )

        args.page_id = str(args.page_id).strip()
        if not re.fullmatch(r"[0-9]+", args.page_id):
            raise ValueError("Facebook Page ID không hợp lệ; phải là chuỗi số ASCII")
        if not args.proxy:
            raise ValueError(
                "Cần proxy trong account/proxy.txt hoặc --proxy trước khi mở trình duyệt"
            )

        commenter = FacebookFanpageCommenter(
            urls=args.urls,
            cookies_file=args.cookies,
            comment_file=args.comment_list,
            page_id=args.page_id,
            proxy=args.proxy,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            num_threads=args.threads,
            headless=args.headless
        )

        await commenter.run()

    except Exception as e:
        safe_error = sanitize_error_text(e)
        message = f"Error: {safe_error}"
        try:
            console.print(f"[bold red]{message}[/bold red]")
        except UnicodeEncodeError:
            print(message.encode("ascii", "backslashreplace").decode("ascii"))
        raise SystemExit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        try:
            console.print("\nStopped by user.")
        except UnicodeEncodeError:
            print("\nProgram stopped by user.")
        raise SystemExit(130)
