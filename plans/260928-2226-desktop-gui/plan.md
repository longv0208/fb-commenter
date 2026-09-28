# Plan: Convert fb-commenter CLI thành Desktop GUI (Electron + Python)

Mục tiêu: bọc tool comment Facebook hiện có thành app desktop Windows, quản lý
nhiều tài khoản FB (cookie + page id + proxy + profile dir), chạy song song nhiều
account, xem log realtime từng account, UI dựng bằng Stitch AI.

## Quyết định kiến trúc chính

- Bridge: **local HTTP + WebSocket** bằng `aiohttp` (đã async, chạy chung event
  loop với Playwright). Electron spawn 1 Python process: `python -m backend.server --port 8787`.
- Store account: **`data\app.db` (SQLite mở rộng)** — thêm bảng `accounts`.
  `PRAGMA journal_mode=WAL`. Giữ nguyên `posts`/`comment_history` (thêm cột
  `account_name` qua `ALTER TABLE` idempotent trong `connect()`).
- Packaging: **electron-builder + PyInstaller onedir** backend (`backend-dist\`),
  dùng Chrome system (`channel="chrome"`), không bundle Chromium.

## Phases

| # | File | Nội dung | Status |
|---|------|----------|--------|
| 01 | phase-01-backend-refactor.md | LogBus, AccountRunner, RunManager + patch commenter | done |
| 02 | phase-02-api-bridge.md | aiohttp HTTP/WS server, REST + event stream | done |
| 03 | phase-03-electron-shell.md | Electron main, spawn Python, preload | done |
| 04 | phase-04-stitch-ui.md | Stitch prompts 5 màn + renderer HTML/JS | done (UI tự code theo design; prompts lưu `stitch-prompts.md` để regenerate bằng Stitch AI) |
| 05 | phase-05-accounts-store.md | Bảng accounts, profile dirs, proxy config | done |
| 06 | phase-06-logging.md | Log per account, WS push, export file | done |
| 07 | phase-07-packaging.md | PyInstaller + electron-builder .exe | script sẵn, cần chạy spike build |
| 08 | phase-08-tests-docs.md | pytest backend, smoke e2e, README | done (28 tests pass) |

## Luồng dữ liệu

```
Electron renderer (HTML/JS)
   |  REST / WS  ws://127.0.0.1:8787
Electron main  ── spawn ──► Python aiohttp server (port 8787)
                              | RunManager (asyncio tasks)
                              ├─ AccountRunner A ─ Playwright Chrome #1 (proxy A, profile A)
                              ├─ AccountRunner B ─ Playwright Chrome #2 (proxy B, profile B)
                              └─ LogBus ──► WS broadcast ──► renderer log view
```
