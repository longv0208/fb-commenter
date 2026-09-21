# Project Changelog

## 2026-09-21

### Automatic Page ID resolution

- Added Page ID resolution with the priority `--page-id` → `account/page_id.txt` → Graph API `GET /v26.0/me?fields=id` using the first non-blank Page Access Token line.
- The token remains required for every run; when resolution is needed, it completes before browser startup.
- Resolved Page IDs are kept in memory and are not written back to disk. The resolver uses the returned `id` and does not verify `type=Page`.
- Added safe failure handling for non-success responses, transport/JSON failures, and missing or non-numeric `id` values without exposing the token; resolver authentication uses an `Authorization: Bearer` header.
- Added unit coverage for resolver request shape, proxy forwarding, HTTP failures, and missing Page IDs.

### Runtime fix documentation

- Documented canonical numeric Facebook post object IDs and rejection of `pfbid` short IDs.
- Documented Page Access Token file requirements and the `--page-token` option.
- Documented JSON, Netscape, semicolon, and fallback cookie parsing behavior.
- Documented graceful Ctrl+C handling, exit status 130, and Playwright cleanup.
- Documented secret-safe logging expectations and current sequential execution limitation.
- Added source-verified architecture, standards, PDR, roadmap, and codebase summary documentation.
