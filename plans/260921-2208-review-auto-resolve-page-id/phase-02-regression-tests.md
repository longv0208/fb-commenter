# Phase 2 — Regression tests

## Context links

- `tests/test_main.py`
- `tests/test_fanpage_commenter.py`
- `main.py`

## Overview

- Priority: P1
- Status: pending
- Goal: cover resolver behavior and CLI integration without live Facebook calls.

## Existing coverage

- Resolver success, endpoint/params, proxy forwarding.
- Non-success response without secret leakage.
- Missing `id` and malformed JSON.
- Existing commenter suite covers URL validation, cleanup, comment behavior, and Graph error redaction.

## Implementation steps

1. Add resolver tests for no-proxy client construction and exact Graph version/fields.
2. Add payload tests for non-numeric strings, booleans, null, list, and empty ID.
3. Add `httpx.HTTPError`/timeout tests; assert safe error text excludes token, response body, and proxy credentials.
4. Add CLI-level tests with patched `argparse`, `resolve_page_id`, `FacebookFanpageCommenter`, and `run()` to prove:
   - explicit `--page-id` skips resolver;
   - `account/page_id.txt` skips resolver;
   - missing Page ID invokes resolver before commenter creation;
   - resolved ID and token are passed to commenter.
5. Add token-file tests for first non-blank line, missing file, and empty file while avoiding real credentials.
6. Keep all HTTP calls mocked; no live Page or token in fixtures.

## Todo list

- [ ] Add invalid-ID and transport-failure cases.
- [ ] Add precedence/fallback integration tests.
- [ ] Add token-file validation tests.
- [ ] Verify tests are deterministic and isolated between fake clients.

## Success criteria

- Every resolver branch has an assertion.
- Tests fail if resolver is called in an explicit-ID path or after browser startup.
- Full suite remains green without network access.
