import re
import unicodedata

HELP_PHRASES = (
    "xin tai lieu",
    "can tai lieu",
    "xin review",
    "hoc o dau",
    "hoc cho nao",
    "can mentor",
    "ai day",
    "sap thi",
    "sap pe",
    "on pe",
    "khong biet hoc",
    "khong biet lam",
    "can support",
)


def fold(text):
    normalized = unicodedata.normalize("NFD", text or "")
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", stripped).lower().strip()


def keyword_match(text, subjects, phrases=None):
    folded = fold(text)
    if not folded:
        return False
    for subject in subjects:
        token = fold(subject)
        if token and re.search(rf"(?<![a-z0-9]){re.escape(token)}\d*(?![a-z])", folded):
            return True
    chosen = HELP_PHRASES if phrases is None else phrases
    return any(fold(phrase) in folded for phrase in chosen)


def hidden_author_ids(path):
    if path is None or not path.is_file():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip().isdigit()
    }
