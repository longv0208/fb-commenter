---
title: "Campaign editor UI"
description: "Add a sidebar view to create/edit campaign JSON via existing /api/campaigns REST"
status: pending
priority: P2
effort: 2h
branch: n/a
tags: [electron, renderer, campaigns, ui]
created: 2026-10-26
---

# Campaign editor UI

## Context links
- Renderer shell: `desktop/renderer/app.js` (hash router, `api.get/post/put`, `esc` idiom)
- Router + sidebar: `desktop/renderer/index.html`
- Existing view pattern to mirror: `desktop/renderer/views/run.{html,js}` and `settings.{html,js}`
- Backend: `backend/server.py` — `list_campaigns` L123, `get_campaign` L132, `put_campaign` L139 (writes ANY name — create works, no DELETE)
- Campaign consumer: `campaign_run.py` `load_campaign` L30-44 (defaults + legacy `use_jev`/`jev_confidence`/`jev_review_all` fallback)
- Real campaign sample: `E:\Telegram Desktop\tool cmt\account\campaigns\fpt_courses.json`

## Campaign JSON schema (what the form writes)

| Key | Type | UI control | Notes |
|---|---|---|---|
| groups | list[str] | textarea, one URL per line | required |
| subjects | list[str] | text input, comma-sep | keywords |
| help_phrases | list[str] | text input, comma-sep | |
| use_phobert | bool | checkbox | write new key (NOT `use_jev`) |
| phobert_threshold | float | number, step 0.05 | write new key |
| phobert_review_all | bool | checkbox | write new key |
| sort_newest | bool | checkbox | |
| max_scrolls | int | number | |
| empty_scroll_limit | int | number | |
| scroll_pixels | int | number | |
| scroll_pause_ms | int | number | |
| scroll_ratio | float | number, step 0.05 | |
| max_comments_per_group | int | number | |
| max_comments_per_run | int | number | |
| cooldown_seconds | int | number | |

On LOAD: map legacy keys → new fields when new key missing:
- `use_phobert` ← `use_phobert ?? use_jev ?? false`
- `phobert_threshold` ← `phobert_threshold ?? jev_confidence ?? 0.8`
- `phobert_review_all` ← `phobert_review_all ?? jev_review_all ?? false`

On SAVE: write ONLY `use_phobert`, `phobert_threshold`, `phobert_review_all`. Drop the three `jev_*` keys entirely — backend keeps backward-compat via `setdefault` anyway.

## Files to create / modify

Create:
- `desktop/renderer/views/campaigns.html` — two-card layout (list left, form right) like `run.html`
- `desktop/renderer/views/campaigns.js` — IIFE module, mirrors `run.js` structure

Modify:
- `desktop/renderer/app.js` — add `campaigns: "views/campaigns.html"` to `routes` (L60-66)
- `desktop/renderer/index.html` — add `<a href="#/campaigns" data-route="campaigns">Campaign</a>` between "Chạy" and "Logs"
- `desktop/renderer/views/settings.html` — remove obsolete JEV API key row (L4-5); settings.js L13 drop `jev_api_key` from PUT body. Optional — flag in todo.

No backend changes needed. `put_campaign` already writes any name; no DELETE (YAGNI).

## Implementation steps

1. Add route entry in `app.js` `routes` object.
2. Add sidebar `<a>` in `index.html` nav (keeps current ordering, Vietnamese label "Campaign").
3. Create `campaigns.html`: left card = list (`<ul>` of names, click → select; top has "+ Mới" button). Right card = form fields per schema table. Bottom toolbar = "Lưu" button + `<span id="camp-msg">`.
4. Create `campaigns.js`:
   - IIFE, `esc` helper copied from `run.js`.
   - `loadList()` → `api.get("/api/campaigns")` → render `<li>` per campaign; mark active.
   - `loadCampaign(name)` → `api.get("/api/campaigns/{name}")` → populate form via legacy-key translation table above.
   - `newCampaign()` → clear form, set name input editable, defaults: `use_phobert=true`, `phobert_threshold=0.8`, `sort_newest=false`, numbers from `load_campaign` setdefaults (30, 4, 700, 4000, 0.4, 5, 15, 120).
   - `save()` → read form → build JSON (split groups textarea by `\n`, filter empty; split subjects/help_phrases by `,`, trim) → `api.put("/api/campaigns/" + encodeURIComponent(name), body)` → msg "Đã lưu." → refresh list.
   - Validate: `name` non-empty + slug-safe (`/[a-zA-Z0-9_-]/`), `groups` non-empty → else show msg and abort.
5. (Optional, recommended) Strip `set-jev` field from `settings.html`/`settings.js` since PhoBERT is local now.
6. Manually verify (see below).

## Todo

- [ ] `app.js` — add `campaigns` route
- [ ] `index.html` — add sidebar link
- [ ] `views/campaigns.html` — list + form markup
- [ ] `views/campaigns.js` — load/list/new/save logic with jev→phobert translation
- [ ] (opt) `views/settings.html`/`settings.js` — remove `jev_api_key` field
- [ ] Manual verification (below)

## Verification

Backend (PowerShell):
```
Invoke-RestMethod http://127.0.0.1:8787/api/campaigns
Invoke-RestMethod http://127.0.0.1:8787/api/campaigns/fpt_courses
$body = @{groups=@("https://fb.com/groups/x"); subjects=@("a"); help_phrases=@(); use_phobert=$true; phobert_threshold=0.8; phobert_review_all=$false; sort_newest=$false; max_scrolls=30; empty_scroll_limit=4; scroll_pixels=700; scroll_pause_ms=4000; scroll_ratio=0.4; max_comments_per_group=5; max_comments_per_run=15; cooldown_seconds=120} | ConvertTo-Json
Invoke-RestMethod -Method Put -Uri http://127.0.0.1:8787/api/campaigns/test1 -Body $body -ContentType "application/json"
```

GUI:
1. `cd desktop; npm start` → click "Campaign" in sidebar → list shows `fpt_courses`.
2. Click `fpt_courses` → form populates; `use_phobert` unchecked (since file has `use_jev:false` and no `use_phobert` — translation works).
3. Edit a field → Lưu → reopen file → confirm `use_phobert`/`phobert_*` keys written, `use_jev`/`jev_*` gone.
4. Click "+ Mới" → fill name `test2` + one group URL → Lưu → `account/campaigns/test2.json` exists.
5. Go to "Chạy" → campaign mode → dropdown shows new campaign.

## Open questions

- Delete campaign button? Currently no DELETE endpoint. Skipped per YAGNI — add later if user asks.
- Should `help_phrases` default to backend `HELP_PHRASES` constant on new campaigns, or empty? Plan: leave empty, user fills.
- Remove `jev_api_key` from settings view, or keep for backward compat? Plan recommends removing (PhoBERT is local); confirm with user.
