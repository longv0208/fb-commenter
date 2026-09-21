# Code Standards

## Structure

Keep CLI orchestration in `main.py` and runtime behavior in `facebook_fanpage_commenter.py`. Add tests under `tests/`. Keep operational documentation under `docs/`; do not place credentials in source, fixtures, or examples.

## Input and validation

- Strip and validate IDs before constructing Graph API URLs.
- Accept only explicitly supported Facebook hosts and URL forms.
- Fail closed for missing token, empty cookie, and empty comment inputs.
- Preserve cookie domain/path data when importing browser exports.
- Treat `pfbid` values as unsupported unless a verified conversion path is added.

## Secrets and logs

- Read Page Access Tokens from a protected file; never hard-code or print them.
- Never log cookie values, token values, or proxy credentials.
- Keep structured API errors limited to status, safe error fields, and redacted messages.
- Update redaction tests whenever error formatting changes.
- Use fake values only in tests and clearly label them as such.

## Async resource lifecycle

Initialize Playwright handles on the instance, close context/browser/Playwright independently, and make cleanup idempotent. `run()` must retain cleanup in `finally`. Ctrl+C and task cancellation must not bypass browser cleanup.

## HTTP behavior

Use the configured Graph API version constant, HTTPS URLs, a bounded timeout, and the configured proxy only when supplied. Page ID resolution must send the Page Access Token through an `Authorization: Bearer <token>` header, validate the returned ID as decimal numeric data, and map HTTP, JSON, and transport failures to generic errors without response bodies or secrets. Return a boolean result from `post_comment()` so the orchestration loop can decide whether to remove a comment from its pending set.

## Tests

At minimum, cover:

- canonical object ID and supported URL conversion;
- malformed and `pfbid` targets;
- cookie format normalization;
- invalid-cookie cleanup;
- missing token/session behavior;
- Graph error redaction;
- cancellation cleanup.

Production Facebook requests are not unit tests. Keep live verification separate, use a controlled Page, and avoid committing live credentials.
