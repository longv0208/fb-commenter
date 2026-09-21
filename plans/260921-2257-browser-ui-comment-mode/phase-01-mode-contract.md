# Phase 1: Mode contract and CLI routing

## Context links

- [Overview](plan.md)
- `main.py`
- `tests/test_main.py`

## Overview

- Priority: P1
- Status: done
- Estimate: 1.5h
- Add an explicit mode boundary while preserving current Graph API defaults.

## Requirements

- Add `--comment-mode` with `graph` and `ui`; default to `graph`.
- Keep existing arguments and default file discovery behavior.
- Graph mode: require/read Page Access Token, resolve Page ID when absent, and pass token to `FacebookFanpageCommenter`.
- UI mode: do not require, read, or resolve a Page Access Token; require a valid numeric Page ID from CLI/file; pass `access_token=None`.
- Keep safe error redaction for both modes.
- Reject unknown modes through argparse and reject invalid/non-ASCII numeric Page IDs before browser work.

## Implementation steps

1. Add the mode argument and include it in the CLI test fixture.
2. Split token-path loading/resolution behind the Graph-mode branch.
3. Pass `comment_mode` to `FacebookFanpageCommenter` without changing existing Graph defaults.
4. Keep page ID loading shared, but make it mandatory for UI mode with a clear error.
5. Preserve all current Graph resolver behavior and tests.

## Related code files

- Modify: `main.py`, `tests/test_main.py`.
- Create/delete: none.

## Success criteria

- Existing Graph tests pass unchanged or with only fixture updates.
- A UI invocation with cookies and Page ID but no `account/page.txt` constructs the commenter successfully.
- UI invocation never calls `resolve_page_id` and never exposes token-file errors.

## Risks and mitigations

- Risk: accidental token read before mode branch. Mitigate by selecting mode before constructing `page_token_path`/reading it.
- Risk: callers instantiate commenter directly. Keep `comment_mode` default `graph` and `access_token` optional only for UI.
