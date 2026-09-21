import argparse
import sys
from rich.console import Console
from rich.prompt import Prompt

console = Console()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Facebook Fanpage Commenter CLI")
    parser.add_argument("--urls", help="List of post IDs or URLs separated by comma")
    parser.add_argument("--cookies", help="Path to cookies.txt file")
    parser.add_argument("--comment-list", help="Path to comment_list.txt file")
    parser.add_argument("--page-id", help="Facebook Page ID")
    parser.add_argument("--proxy", help="Proxy URL (e.g. http://user:pass@ip:port)")
    parser.add_argument("--delay-min", type=int, default=1, help="Minimum delay in minutes")
    parser.add_argument("--delay-max", type=int, default=60, help="Maximum delay in minutes")
    parser.add_argument("--threads", type=int, default=3, help="Number of concurrent threads")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Interactive mode if arguments are missing
    if not all([args.urls, args.cookies, args.comment_list, args.page_id]):
        console.print("[yellow]Some required arguments are missing. Entering interactive mode...[/yellow]")

        if not args.urls:
            args.urls = Prompt.ask("Enter post IDs or URLs (comma separated)", default="")

        if not args.cookies:
            args.cookies = Prompt.ask("Enter path to cookies.txt file", default="cookies.txt")

        if not args.comment_list:
            args.comment_list = Prompt.ask("Enter path to comment_list.txt file", default="comment_list.txt")

        if not args.page_id:
            args.page_id = Prompt.ask("Enter Facebook Page ID", default="")

        if not args.proxy:
            use_proxy = Prompt.ask("Do you want to use proxy? (y/n)", default="n")
            if use_proxy.lower() == "y":
                args.proxy = Prompt.ask("Enter proxy URL (e.g. http://user:pass@ip:port)", default="")

        args.delay_min = int(Prompt.ask("Minimum delay (minutes)", default=1))
        args.delay_max = int(Prompt.ask("Maximum delay (minutes)", default=60))
        args.threads = int(Prompt.ask("Number of threads", default=3))
        args.headless = Prompt.ask("Run in headless mode? (y/n)", default="n") == "y"
        args.verbose = Prompt.ask("Enable verbose logging? (y/n)", default="n") == "y"

    return args