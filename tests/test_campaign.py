import json

import pytest

from campaign_run import load_campaign, select_posts
from campaign_store import already_commented, connect, save_comment
from jev_client import JevError, review_post
from post_rules import keyword_match


def test_keyword_matches_subject_or_help_phrase():
    assert keyword_match("GIẢI QUYẾT NỖI LO CÁC MÔN TOÁN (MAE - MAD - MAS)", ["MAD"])
    assert keyword_match("Có ai file PE CSD201 không", ["CSD201"])
    assert keyword_match("Mình cần tài liệu ạ", [])
    assert keyword_match("pass rồi nhưng vẫn cần tài liệu", ["CSD201"])
    assert not keyword_match("hôm nay trời đẹp", ["CSD201"])


def test_hidden_author_and_previous_comment_are_skipped(tmp_path):
    db = connect(tmp_path / "app.db")
    save_comment(db, "https://www.facebook.com/groups/a/posts/1", "ib", True)
    posts = [
        {"post_url": "https://www.facebook.com/groups/a/posts/1", "author_id": "9", "text": "CSD201"},
        {"post_url": "https://www.facebook.com/groups/a/posts/2", "author_id": "55", "text": "CSD201"},
        {"post_url": "https://www.facebook.com/groups/a/posts/3", "author_id": "7", "text": "cần tài liệu"},
        {"post_url": "https://www.facebook.com/groups/a/posts/4", "author_id": "", "text": "ảnh"},
    ]
    selected, hidden_count = select_posts(
        posts,
        {"subjects": ["CSD201"], "jev_review_all": False},
        {"55"},
        "999",
        db,
    )
    assert hidden_count == 1
    assert [item["post_url"] for item in selected] == [
        "https://www.facebook.com/groups/a/posts/3"
    ]
    assert already_commented(db, posts[0]["post_url"])


def test_load_campaign_requires_groups(tmp_path):
    folder = tmp_path / "account" / "campaigns"
    folder.mkdir(parents=True)
    (folder / "fpt.json").write_text(json.dumps({"groups": [], "subjects": ["CSD201"]}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_campaign(tmp_path, "fpt")


def test_review_post_reads_choice(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"answers": {"action": {"choice": "comment", "confidence": 0.91}}}
            ).encode()

    monkeypatch.setattr("jev_client.urlopen", lambda *args, **kwargs: Response())
    label, confidence = review_post("cần tài liệu CSD201", ["CSD201"], api_key="secret")
    assert label == "comment"
    assert confidence == 0.91


def test_review_post_rejects_bad_payload(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"answers": {}}'

    monkeypatch.setattr("jev_client.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(JevError):
        review_post("xin", ["CSD201"], api_key="secret")
