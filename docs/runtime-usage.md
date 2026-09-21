# Runtime Usage

## Install

From `tools/fb-commenter`:

```bash
python -m pip install -r requirements.txt
playwright install chromium
python main.py --help
```

The supported runtime is `main.py`, which starts Playwright, loads cookies, validates the Facebook session, and submits comments through the Graph API.

## Required inputs

| Input | CLI option or default | Requirement |
|---|---|---|
| Facebook post targets | `--urls` or `account/post_ids.txt` | Comma-separated canonical numeric post IDs or supported Facebook URLs. Do not use profile/page IDs as post IDs. |
| Facebook Page ID | `--page-id`, `account/page_id.txt`, or auto-resolved | Resolution priority is `--page-id` → `account/page_id.txt` → Graph API `GET /v26.0/me?fields=id`; the Page Access Token remains required for every run. Auto-resolution accepts only a decimal numeric ID. |
| Page Access Token | `--page-token` or `account/page.txt` | A non-empty file; the first non-blank line is read. The token is sent only in the HTTPS Graph API request. |
| Browser cookies | `--cookies` or `account/cookies.txt` | Non-empty cookies in one supported format, with an unexpired session. The session normally needs both `c_user` and `xs`. |
| Comments | `--comment-list` or `comments/comment_list.txt` | One non-blank comment per line. |

The fallback files are resolved relative to the project layout. Explicit options are preferred for repeatable runs.

## Canonical Facebook post IDs

The Graph API request targets `/{GRAPH_API_VERSION}/{object_id}/comments`. Use a numeric object ID:

```text
<Page ID>_<post ID>
```

Examples:

```text
1234567890_9876543210
```

A bare numeric post ID is rejected; the effective Page ID (explicit, file-based, or auto-resolved) must match the owner portion of the canonical object ID. Supported URL forms are:

- `https://www.facebook.com/<numeric-page-id>/posts/<numeric-post-id>`
- `https://www.facebook.com/permalink.php?story_fbid=<numeric-post-id>&id=<numeric-page-id>`

The parser also accepts the `m.facebook.com` host. It rejects non-Facebook hosts, malformed IDs, and `pfbid...` short IDs because the current Graph API adapter cannot convert those short IDs. Convert a short URL to a canonical numeric object ID before running.

## Page Access Token

Create a local token file and protect it from source control. For the default layout:

When `--page-id` and `account/page_id.txt` are both absent, the CLI calls Graph API `/v26.0/me?fields=id` with this token and uses the returned ID. The token is sent in an `Authorization: Bearer <token>` header, not in the query string. The resolver accepts only a decimal numeric ID; missing, non-numeric, boolean, or otherwise malformed IDs fail closed. HTTP, JSON, and transport failures stop before browser startup with generic safe errors; response bodies and token values are not included. The resolver does not independently verify that the returned object is a Page, and the resolved Page ID is not written back to disk.

```text
account/page.txt
```

The file must contain at least one non-blank line. With a custom path:

```bash
python main.py --page-token path/to/page-token.txt --page-id 1234567890 --urls 1234567890_9876543210
```

Do not place the token in `--urls`, comments, source code, or a shell transcript. The CLI does not print the token. An absent or empty file stops the run before browser startup. A token that is present but invalid causes Graph API failure and the token value is not included in the structured error details.

## Cookie formats

`facebook_fanpage_commenter.py` accepts these formats:

1. A JSON array of Playwright cookie objects. Each object needs `name` and `value`; `domain` defaults to `.facebook.com` and `path` defaults to `/`. A `url` field is removed because the browser context uses domains.
2. Netscape cookie export lines with tab-separated fields. `#HttpOnly_` prefixes are supported.
3. Semicolon-separated `name=value` pairs, for example `c_user=...; xs=...`.
4. A single fallback value is treated as a `c_user` value, but this is normally insufficient for authentication.

Use a fresh export from the same Facebook account and retain the cookie domain/path metadata when possible. The file must not be committed or shared. If Facebook redirects to login, refresh the cookie export; the runtime reports that an unexpired `c_user` and `xs` session is required.

## Example run

```bash
python main.py \
  --urls "1234567890_9876543210,1234567890_9876543211" \
  --cookies account/cookies.txt \
  --comment-list comments/comment_list.txt \
  --page-id 1234567890 \
  --page-token account/page.txt \
  --delay-min 1 \
  --delay-max 60 \
  --headless
```

`--proxy` may be supplied as a Playwright/httpx proxy URL when required. Keep credentials out of logs and process listings where possible. `--threads` is accepted for CLI compatibility but the current run method executes one async commenting loop; it does not provide parallel posting.

## Graceful Ctrl+C

Press Ctrl+C once to stop. The top-level runner prints `Stopped by user.` and exits with status 130. During the delay, cancellation is handled and the browser context, browser, and Playwright process are closed in `finally` cleanup. A second interrupt may terminate the process before cleanup completes.

## Logging and secret handling

The runtime may log post IDs, the public Page ID resolved by the CLI, HTTP status, validation failures, and a redacted Graph API error summary. It does not intentionally log Page Access Token or cookie values. Error messages may include local file paths, so keep secret files in a protected directory. Do not enable verbose logs when collecting diagnostics that could expose user-provided comments or infrastructure details.
