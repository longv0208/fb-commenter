# Phase 1 — Resolver contract

## Context links

- `main.py:16-33`
- `docs/runtime-usage.md`
- `docs/code-standards.md`

## Overview

- Priority: P1
- Status: pending
- Goal: define and enforce the safe contract for Page ID resolution.

## Key insights

- `/v26.0/me?fields=id` is already used with a 30-second timeout and optional proxy.
- Current validation accepts any truthy `id`; downstream documentation requires a numeric Page ID.
- HTTP failures are mapped to a generic error, while transport exceptions currently rely on top-level handling.

## Implementation steps

1. Preserve the existing precedence: `--page-id` -> `account/page_id.txt` -> Graph API resolver.
2. Validate the resolved payload is an object containing a non-empty numeric `id`; reject lists, nulls, booleans, and non-numeric values.
3. Normalize resolver HTTP, JSON, timeout, and transport failures to safe actionable errors without response body or token.
4. Preserve `GRAPH_API_VERSION`, HTTPS endpoint, bounded timeout, and optional proxy behavior.
5. Keep the resolved ID in memory only; do not write `account/page_id.txt`.
6. Confirm explicit Page ID bypasses the network resolver and remains unchanged for backward compatibility.

## Todo list

- [ ] Agree numeric-ID and error-message contract.
- [ ] Update `main.py` only after test cases are defined.
- [ ] Check no token appears in exception text or logs.

## Success criteria

- Valid numeric Page token response returns a string ID.
- Invalid payload and network failure stop before commenter/browser creation.
- Existing explicit Page ID path makes no `/me` request.

## Risks and security

- Do not expose Graph response body, request URL, token, or proxy credentials.
- Do not infer a different Page when token resolution fails.
