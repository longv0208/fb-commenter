"""aiohttp local API: REST + WebSocket for the Electron desktop shell."""
import asyncio
import json
import logging
from pathlib import Path

from aiohttp import web, WSMsgType

from backend import file_logs, store
from backend.log_bus import attach_root, log_bus
from backend.run_manager import RunManager
from backend.schemas import account_from_payload, run_from_payload

logger = logging.getLogger("fb_commenter")

BASE_DIR = Path(__file__).resolve().parents[1]
PARENT_DIR = BASE_DIR.parents[1]


# ---------- helpers ----------

def _json(data, status=200):
    return web.json_response(data, status=status)


def _err(exc, status=400):
    return _json({"error": str(exc)}, status=status)


async def _body(request):
    try:
        return await request.json()
    except Exception:
        return {}


# ---------- REST handlers ----------

async def health(request):
    return _json({"ok": True})


async def list_accounts(request):
    return _json(store.list_accounts(request.app["db"]))


async def create_account(request):
    try:
        acc = account_from_payload(await _body(request))
    except ValueError as e:
        return _err(e)
    return _json(store.upsert_account(request.app["db"], acc), status=201)


async def update_account(request):
    name = request.match_info["name"]
    existing = store.get_account(request.app["db"], name)
    if not existing:
        return _err(ValueError("Không thấy account"), 404)
    try:
        acc = account_from_payload(await _body(request), partial=True)
    except ValueError as e:
        return _err(e)
    existing.update(acc)
    existing["name"] = name
    return _json(store.upsert_account(request.app["db"], existing))


async def delete_account(request):
    name = request.match_info["name"]
    await request.app["runs"].stop(name)
    store.delete_account(request.app["db"], name)
    file_logs.detach(name)
    return _json({"ok": True})


async def list_runs(request):
    return _json(request.app["runs"].status())


async def start_run(request):
    name = request.match_info["name"]
    account = store.get_account(request.app["db"], name)
    if not account:
        return _err(ValueError("Không thấy account"), 404)
    try:
        opts = run_from_payload(await _body(request))
        mode = opts.pop("mode")
        file_logs.attach(name)
        result = await request.app["runs"].start(account, mode, opts)
    except (ValueError, RuntimeError) as e:
        return _err(e)
    return _json(result)


async def stop_run(request):
    return _json(await request.app["runs"].stop(request.match_info["name"]))


async def stop_all(request):
    return _json(await request.app["runs"].stop_all())


async def get_settings(request):
    return _json(store.get_settings(request.app["db"]))


async def put_settings(request):
    data = await _body(request)
    store.set_settings(request.app["db"], data)
    return _json(store.get_settings(request.app["db"]))


async def list_comment_files(request):
    comments_dir = PARENT_DIR / "comments"
    files = []
    if comments_dir.is_dir():
        for f in sorted(comments_dir.glob("*.txt")):
            files.append({"name": f.name, "path": str(f)})
    return _json(files)


async def list_campaigns(request):
    camp_dir = PARENT_DIR / "account" / "campaigns"
    files = []
    if camp_dir.is_dir():
        for f in sorted(camp_dir.glob("*.json")):
            files.append({"name": f.stem, "path": str(f)})
    return _json(files)


async def get_campaign(request):
    path = PARENT_DIR / "account" / "campaigns" / f"{request.match_info['name']}.json"
    if not path.is_file():
        return _err(ValueError("Không thấy campaign"), 404)
    return _json(json.loads(path.read_text(encoding="utf-8")))


async def put_campaign(request):
    data = await _body(request)
    path = PARENT_DIR / "account" / "campaigns" / f"{request.match_info['name']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return _json({"ok": True})


# ---------- WebSocket ----------

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    request.app["ws_clients"].add(ws)

    async def pump():
        try:
            async for entry in log_bus.subscribe("*"):
                if ws.closed:
                    break
                await ws.send_json({"type": "log", **entry})
        except Exception:
            pass

    async def status_tick():
        while not ws.closed:
            try:
                await ws.send_json(
                    {"type": "status", "runs": request.app["runs"].status()}
                )
            except Exception:
                break
            await asyncio.sleep(1)

    pump_task = asyncio.create_task(pump())
    tick_task = asyncio.create_task(status_tick())
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                pass  # client->server commands reserved
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                break
    finally:
        pump_task.cancel()
        tick_task.cancel()
        request.app["ws_clients"].discard(ws)
    return ws


# ---------- app factory ----------

def create_app():
    attach_root()
    app = web.Application()
    app["db"] = store.connect()
    app["runs"] = RunManager()
    app["ws_clients"] = set()
    log_bus.bind_loop(asyncio.get_event_loop())

    app.router.add_get("/api/health", health)
    app.router.add_get("/api/accounts", list_accounts)
    app.router.add_post("/api/accounts", create_account)
    app.router.add_put("/api/accounts/{name}", update_account)
    app.router.add_delete("/api/accounts/{name}", delete_account)
    app.router.add_get("/api/runs", list_runs)
    app.router.add_post("/api/runs/{name}/start", start_run)
    app.router.add_post("/api/runs/{name}/stop", stop_run)
    app.router.add_post("/api/runs/stop-all", stop_all)
    app.router.add_get("/api/settings", get_settings)
    app.router.add_put("/api/settings", put_settings)
    app.router.add_get("/api/comments", list_comment_files)
    app.router.add_get("/api/campaigns", list_campaigns)
    app.router.add_get("/api/campaigns/{name}", get_campaign)
    app.router.add_put("/api/campaigns/{name}", put_campaign)
    app.router.add_get("/ws", ws_handler)
    return app


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    web.run_app(create_app(), host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
