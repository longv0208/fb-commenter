# Development Roadmap

## Current phase: Runtime hardening

Status: Implemented in the current working tree; production verification remains outstanding.

Completed:

- Canonical numeric post-ID normalization and supported Facebook URL parsing.
- Page Access Token file loading through `--page-token` or `account/page.txt`.
- Automatic Page ID resolution through Graph API `/v26.0/me?fields=id` when no Page ID file/option is configured.
- Cookie import for JSON, Netscape, and semicolon formats.
- Login failure cleanup and idempotent browser teardown.
- Ctrl+C handling with exit status 130.
- Redacted Graph API error details.
- Unit coverage for URL normalization, cleanup on invalid cookie, and token redaction.

Next priorities:

1. Add unit coverage for each cookie format, malformed inputs, cancellation, and token-file validation.
2. Decide whether `--threads` should be removed or implemented as genuine bounded concurrency.
3. Add controlled integration verification against a test Page and document required Graph API permissions.
4. Add retry/backoff policy and an explicit terminal outcome for permanently invalid post IDs or permissions.
