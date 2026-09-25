import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

JEV_URL = "https://api.typesafe.ai/v1/systemone"


class JevError(RuntimeError):
    pass


def review_post(text, subjects, api_key=None, timeout=30):
    """Ask Jev for comment or skip. Returns (label, confidence)."""
    key = api_key or os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise JevError("Thiếu JEV_API_KEY")
    subject_list = ", ".join(subjects) or "(không khai mã môn)"
    body = {
        "state": (text or "")[:4000],
        "model": "jev-latest",
        "questions": {
            "action": {
                "type": "choice",
                "instructions": (
                    "Decide whether this Facebook post should receive a short reply "
                    "inviting the author to message the page. Choose comment when the "
                    f"post names one of these subjects ({subject_list}) or asks for "
                    "materials, a class, a mentor, or exam help. Choose skip otherwise."
                ),
                "criteria": {
                    "comment": "Names a listed subject or asks for study help",
                    "skip": "Not a request for those subjects or study help",
                },
            }
        },
    }
    request = Request(
        JEV_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        raise JevError(sanitize_jev_error(error)) from None
    answer = (payload.get("answers") or {}).get("action") or {}
    label = answer.get("choice")
    confidence = answer.get("confidence")
    if label not in {"comment", "skip"} or not isinstance(confidence, (int, float)):
        raise JevError("Jev trả về không đúng nhãn comment/skip")
    return label, float(confidence)


def sanitize_jev_error(error):
    text = str(error)
    return text.replace(os.environ.get("JEV_API_KEY", " "), "<redacted>")[:300]
