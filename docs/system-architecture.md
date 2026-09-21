# System Architecture

## Runtime flow

```text
main.py
  -> resolve CLI values and account/* defaults
  -> read first non-blank Page Access Token line (required for every run)
  -> resolve Page ID with priority: --page-id -> account/page_id.txt
  -> otherwise GET /v26.0/me?fields=id with Authorization: Bearer <token> before browser startup
  -> construct FacebookFanpageCommenter with Page ID and token
  -> run()
       -> login_with_cookie()
            -> start Playwright Chromium
            -> add normalized cookies
            -> open facebook.com and detect login redirect
       -> comment_random()
            -> choose a comment and target
            -> normalize target to a Graph object ID
            -> POST /v26.0/{object_id}/comments through httpx
            -> wait for a random delay
       -> close_browser() in finally
```

## Components

| Component | Responsibility |
|---|---|
| `main.py` | Canonical CLI entry point, default-file discovery, token-file validation, Page ID resolution, top-level error and Ctrl+C handling. |
| `facebook_fanpage_commenter.py` | Cookie parsing, Facebook session setup, post-ID normalization, Graph API requests, retry-loop orchestration, and resource cleanup. |
| `cli.py` | Older interactive argument parser; it is not wired into the documented runtime and does not collect a Page Access Token. |
| `config.py` | Legacy configuration/logging helper; `main.py` currently performs its own argument setup. |
| `tests/test_fanpage_commenter.py` | Tests for invalid-cookie cleanup, comment loading, post-ID normalization, and token redaction. |

## Authentication boundaries

Browser authentication uses cookies only to establish a Facebook session in Playwright. Comment submission uses the Page Access Token in an HTTPS `httpx` request to Graph API version `v26.0`. Page ID resolution sends the token as `Authorization: Bearer <token>` and not as a query parameter. The two credentials serve different purposes and both are required for a normal run. Resolution accepts only a decimal numeric `id`; missing or malformed values fail closed. The code does not verify `type=Page`, and a resolved ID is kept in memory rather than persisted.

## Post target normalization

The post-ID normalizer accepts a numeric object ID (`page_post`) or supported Facebook post URLs. It derives the Page owner from the URL and requires that owner to match the configured `page_id`. Bare numeric IDs, `pfbid` identifiers, and unrelated hosts fail validation before an HTTP request is made.

## Failure and cleanup behavior

- Missing or empty token files fail before `FacebookFanpageCommenter` is constructed.
- If no Page ID is configured, an unsuccessful `/me?fields=id` response, transport failure, malformed JSON, or missing/non-numeric `id` fails before browser startup. Resolver transport and HTTP errors are generic and do not include response bodies or token values.
- Missing/empty comment files fail during construction.
- Invalid cookies or a login-page redirect raise a runtime error and close partially initialized Playwright resources.
- HTTP and validation failures return `False` from `post_comment()` and are summarized without including token values.
- `run()` always calls `close_browser()`, including cancellation and login failures.

## Current limitations

- The current commenting loop is sequential even though `--threads` and `num_threads` exist.
- Failed comments remain in the in-memory list and are retried after a delay; operators should monitor invalid IDs, permissions, and token status rather than assume completion.
- No production Facebook API test is included in the repository. Tests use local fixtures and mocks.
