import os
import logging
from typing import Optional

class Config:
    def __init__(self, args):
        self.urls = self.parse_urls(args.urls)
        self.cookies_file = args.cookies
        self.comment_file = args.comment_list
        self.page_id = args.page_id
        self.proxy = args.proxy
        self.delay_min = args.delay_min
        self.delay_max = args.delay_max
        self.num_threads = args.threads
        self.headless = args.headless
        self.verbose = args.verbose

        self.setup_logging()

    def parse_urls(self, urls_str: str) -> list:
        if not urls_str:
            return []
        return [url.strip() for url in urls_str.split(",") if url.strip()]

    def setup_logging(self):
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("fb_commenter.log"),
                logging.StreamHandler()
            ]
        )
        logging.info("Configuration loaded successfully")