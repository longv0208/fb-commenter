# Project Overview and Product Development Requirements

## Product overview

Facebook Fanpage Commenter is a Python CLI that loads a Facebook browser session from cookies, selects comments from a text file, and submits them to Page posts through the Facebook Graph API. It is intended for authorized Page operators and controlled testing only.

## Scope

In scope:

- Playwright Chromium session bootstrap with imported cookies.
- Canonical numeric Facebook post-ID validation and supported URL conversion.
- Page Access Token loading from a local file.
- Graph API comment submission through `httpx`.
- Random selection and delay between sequential comments.
- Proxy forwarding and graceful resource cleanup.

Out of scope in the current implementation:

- Converting `pfbid` short IDs.
- Actual concurrent posting despite the compatibility `--threads` option.
- Production monitoring, token renewal, or automatic cookie refresh.
- GUI workflows.

## Requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| PDR-01 | Accept canonical numeric object IDs and supported Facebook post URLs belonging to the configured Page. | `normalize_post_id()` returns `<page>_<post>`, validates the owner against `page_id`, and rejects malformed/`pfbid` values. |
| PDR-02 | Require a non-empty Page Access Token file. | `main.py` validates the first non-blank line before startup. |
| PDR-03 | Resolve a Page ID safely when no explicit ID is configured. | `main.py` calls `/v26.0/me?fields=id` with `Authorization: Bearer <token>`, accepts only a decimal numeric `id`, keeps it in memory, and fails closed with generic errors on HTTP, JSON, transport, or malformed-payload failures. |
| PDR-04 | Support JSON, Netscape, and semicolon cookie exports. | `load_browser_cookies()` normalizes each documented format. |
| PDR-05 | Detect expired/invalid browser sessions. | Login redirect or email input raises a runtime error. |
| PDR-06 | Avoid secret disclosure in diagnostics. | Graph error messages redact token-like values; token/cookie values are not intentionally logged. |
| PDR-07 | Stop safely on Ctrl+C. | Top-level handler prints a user-facing stop message, exits 130, and `run()` cleans resources. |
| PDR-08 | Keep API calls bounded and proxy-aware. | `httpx.AsyncClient` uses a 30-second timeout and optional proxy. |

## Non-functional requirements

- Credentials must remain outside version control.
- Validation errors should occur before network calls when possible.
- Browser resources must be closed on success, failure, and cancellation.
- Documentation must not claim parallel execution while the loop is sequential.

## Operational acceptance checklist

1. Run `python main.py --help`.
2. Supply a canonical post object ID, protected token file, valid cookie export, and test comment file; provide a controlled Page ID explicitly or allow safe auto-resolution from the token.
3. Verify a login failure closes browser resources.
4. Verify Ctrl+C produces a clean stop message and no token/cookie value in logs.
5. Review Graph API permissions and Page policy before any broader run.
