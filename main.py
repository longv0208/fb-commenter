import asyncio
import argparse
import logging
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

from facebook_fanpage_commenter import FacebookFanpageCommenter

console = Console()

async def main():
    parser = argparse.ArgumentParser(description="Facebook Fanpage Commenter CLI")
    parser.add_argument("--urls", help="List of post IDs or URLs separated by comma")
    parser.add_argument("--cookies", help="Path to cookies.txt file")
    parser.add_argument("--comment-list", help="Path to comment_list.txt file")
    parser.add_argument("--page-id", help="Facebook Page ID")
    parser.add_argument("--proxy", help="Proxy URL (e.g. http://user:pass@proxy-ip:port)")
    parser.add_argument("--delay-min", type=int, default=1, help="Minimum delay in minutes")
    parser.add_argument("--delay-max", type=int, default=60, help="Maximum delay in minutes")
    parser.add_argument("--threads", type=int, default=3, help="Number of concurrent threads")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Auto-detect files from parent folder
    base_dir = Path(__file__).parent
    parent_dir = base_dir.parent

    if not args.urls:
        post_ids_path = parent_dir / "account" / "post_ids.txt"
        if post_ids_path.exists():
            args.urls = post_ids_path.read_text().strip()
        else:
            args.urls = "1234567890,9876543210"

    if not args.cookies:
        cookies_path = parent_dir / "account" / "cookies.txt"
        if cookies_path.exists():
            args.cookies = str(cookies_path)
        else:
            args.cookies = str(base_dir / "cookies.txt")

    if not args.comment_list:
        comment_path = parent_dir / "comments" / "comment_list.txt"
        if comment_path.exists():
            args.comment_list = str(comment_path)
        else:
            args.comment_list = str(base_dir / "comment_list.txt")

    if not args.page_id:
        page_id_path = parent_dir / "account" / "page_id.txt"
        if page_id_path.exists():
            args.page_id = page_id_path.read_text().strip()
        else:
            args.page_id = "1234567890"

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console)]
    )

    console.print("[bold green]Starting Facebook Fanpage Commenter...[/bold green]")

    try:
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
        console.print(f"[bold red]Error: {e}[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())