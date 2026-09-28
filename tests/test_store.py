from pathlib import Path

from backend import store


def test_account_crud_and_migration(tmp_path):
    db = store.connect(tmp_path / "app.db")
    assert store.list_accounts(db) == []

    store.upsert_account(db, {
        "name": "a1", "cookie": "c_user=1;xs=2", "page_id": "99",
        "proxy": "http://h:1", "use_profile": True,
    })
    acc = store.get_account(db, "a1")
    assert acc["page_id"] == "99" and acc["use_profile"] == 1

    # update
    store.upsert_account(db, {"name": "a1", "page_id": "77"})
    assert store.get_account(db, "a1")["page_id"] == "77"

    # settings
    store.set_settings(db, {"jev_api_key": "k1"})
    assert store.get_settings(db)["jev_api_key"] == "k1"

    store.delete_account(db, "a1")
    assert store.list_accounts(db) == []

    # migration idempotent: reconnect same db
    db2 = store.connect(tmp_path / "app.db")
    cols = {r["name"] for r in db2.execute("PRAGMA table_info(posts)")}
    assert "account_name" in cols
