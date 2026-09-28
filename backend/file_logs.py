"""Per-account rotating file log handlers."""
import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[1] / "data" / "logs"

_handlers = {}  # account -> FileHandler


def attach(account, logger_name="fb_commenter"):
    """Attach a FileHandler writing to data/logs/<account>-<date>.log."""
    detach(account)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y%m%d")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in account)
    path = LOG_DIR / f"{safe}-{day}.log"
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.addFilter(lambda r: getattr(r, "account", "system") in (account, "system"))
    logging.getLogger(logger_name).addHandler(handler)
    _handlers[account] = handler
    return path


def detach(account, logger_name="fb_commenter"):
    handler = _handlers.pop(account, None)
    if handler:
        try:
            logging.getLogger(logger_name).removeHandler(handler)
            handler.close()
        except Exception:
            pass
