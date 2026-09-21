# Codebase Summary

## Purpose

Facebook Fanpage Commenter is a Python CLI for authorized Page operators. It imports a browser session from cookies, validates Facebook post targets, and submits comments through the Facebook Graph API.

## Runtime structure

- `main.py` is the canonical async CLI entry point. It loads files and CLI values, validates the Page Access Token, resolves a Page ID when needed, and handles top-level errors and Ctrl+C.
- `facebook_fanpage_commenter.py` owns cookie parsing, Playwright login, post-ID normalization, Graph API comment requests, delay orchestration, and cleanup.
- `cli.py` and `config.py` are legacy helpers and are not used by the documented runtime.
- `tests/test_main.py` covers Page ID resolver request shape, proxy forwarding, numeric payload validation, missing IDs, malformed responses, and transport-error secret handling.
- `tests/test_fanpage_commenter.py` covers cookie/session behavior, post-ID normalization, cleanup, and Graph error redaction.

## Page ID resolution

When no explicit `--page-id` or `account/page_id.txt` value exists, `main.py` calls `GET https://graph.facebook.com/v26.0/me?fields=id`. The Page Access Token is sent in an `Authorization: Bearer <token>` header. The resolver accepts only a decimal numeric ID, keeps it in memory, and never writes it to disk. HTTP, JSON, malformed-payload, and transport failures stop startup with generic safe errors that do not expose the token or response body.

## Comment flow

The runtime starts Playwright only after token validation and, when auto-resolution is used, Page ID resolution succeed. It imports supported cookie formats, rejects login redirects, normalizes canonical numeric object IDs or supported Facebook URLs, and posts to `/{GRAPH_API_VERSION}/{object_id}/comments` with `httpx`. Targets with a bare numeric post ID, unsupported host, malformed ID, `pfbid` short ID, or mismatched Page owner fail closed before posting.

## Security and operational constraints

Tokens, cookies, and proxy credentials are local secrets and must remain outside source control. Logs may include public IDs and safe status details but must not include credential values. Posting is sequential despite the compatibility `--threads` option, and browser resources are closed in `finally` blocks on success, failure, or cancellation.

## Source of truth

This summary was generated after running Repomix over the current working tree. Verify behavior against the source files before documenting new interfaces or production assumptions.
