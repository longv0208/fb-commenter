from types import SimpleNamespace

import pytest

import main


class FakeCommenter:
    instances = []

    def __init__(self, **kwargs):
        type(self).instances.append(kwargs)

    async def run(self):
        return None


def cli_args(page_id=None):
    return SimpleNamespace(
        urls="",
        cookies=None,
        comment_list=None,
        page_id=page_id,
        proxy=None,
        delay_min=1,
        delay_max=1,
        threads=1,
        headless=False,
        verbose=False,
    )


@pytest.mark.asyncio
async def test_main_uses_explicit_page_id(monkeypatch, tmp_path):
    (tmp_path / "account").mkdir()
    monkeypatch.setattr(main, "__file__", str(tmp_path / "tools" / "fb-commenter" / "main.py"))
    monkeypatch.setattr(main.argparse.ArgumentParser, "parse_args", lambda self: cli_args("123"))
    FakeCommenter.instances = []
    monkeypatch.setattr(main, "FacebookFanpageCommenter", FakeCommenter)

    await main.main()

    built = FakeCommenter.instances[0]
    assert built["page_id"] == "123"
    assert "access_token" not in built


@pytest.mark.asyncio
async def test_main_uses_page_id_file(monkeypatch, tmp_path):
    (tmp_path / "account").mkdir()
    (tmp_path / "account" / "page_id.txt").write_text("456\n", encoding="utf-8")
    monkeypatch.setattr(main, "__file__", str(tmp_path / "tools" / "fb-commenter" / "main.py"))
    monkeypatch.setattr(main.argparse.ArgumentParser, "parse_args", lambda self: cli_args())
    FakeCommenter.instances = []
    monkeypatch.setattr(main, "FacebookFanpageCommenter", FakeCommenter)

    await main.main()

    assert FakeCommenter.instances[0]["page_id"] == "456"


@pytest.mark.asyncio
async def test_main_requires_page_id(monkeypatch, tmp_path):
    (tmp_path / "account").mkdir()
    monkeypatch.setattr(main, "__file__", str(tmp_path / "tools" / "fb-commenter" / "main.py"))
    monkeypatch.setattr(main.argparse.ArgumentParser, "parse_args", lambda self: cli_args())
    monkeypatch.setattr(main, "FacebookFanpageCommenter", FakeCommenter)

    with pytest.raises(SystemExit):
        await main.main()
