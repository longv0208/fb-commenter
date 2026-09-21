---
title: "Chrome UI comment mode for Facebook Fanpages"
description: "Add an opt-in Playwright browser mode that switches to the granted Page identity and submits comments without a Page Access Token, while preserving Graph API mode."
status: done
priority: P1
effort: 8h
branch: not-a-git-repository
tags: [facebook, playwright, fanpage, commenting, graph-api]
created: 2026-09-21
---

## Goal

Add a minimal, opt-in `ui` comment mode. The existing Graph API path remains the default and keeps its Page Access Token and object-ID behavior. UI mode uses the authenticated cookie session, switches the browser to the configured Page, opens each target post, enters the comment, and submits it through Facebook UI.

## Scope

- Modify `main.py`, `facebook_fanpage_commenter.py`, and their existing tests only.
- Do not change project documentation.
- Do not call Graph API or load `account/page.txt` in UI mode.
- Keep token redaction and current cleanup/error behavior.

## Phases

1. [Phase 1: Mode contract and CLI routing](phase-01-mode-contract.md) — add mode selection and isolate token requirements.
2. [Phase 2: Playwright Page-identity comment flow](phase-02-playwright-page-comment.md) — implement browser navigation, Page switching, composer interaction, and result detection.
3. [Phase 3: Regression and UI-flow tests](phase-03-regression-tests.md) — extend existing tests with mocked Playwright/CLI boundaries.
4. [Phase 4: Verification and rollout](phase-04-verification.md) — run tests, compile checks, and manual smoke test with a non-sensitive test post.

## Key decisions

- Flag: `--comment-mode {graph,ui}`, default `graph` for backward compatibility.
- UI mode requires a numeric `--page-id` or existing `account/page_id.txt`; cookies remain the login source. Page Access Token is optional and ignored.
- Graph mode remains unchanged except for explicit mode dispatch.
- UI target handling accepts Facebook post URLs and existing `page_id_post_id` inputs; Graph normalization stays strict and unchanged.
- Use resilient role/text locators with locale alternatives and visible `contenteditable` fallback; do not depend on generated CSS class names.
- Fail the current target without automatic retry when identity switching, navigation, composer discovery, or submission cannot be verified.

## Dependencies and risks

- Facebook UI labels/DOM may vary by locale, account state, Page experience, or checkpoint. Keep selector alternatives centralized and require a visible/verified state before submitting.
- Cookie sessions may expire or require an interactive checkpoint; document this in runtime error text, not project docs.
- Page permissions must allow commenting as the Page; UI mode cannot elevate permissions.
- UI mode should default to headed operation in normal CLI usage; retain `--headless` as an explicit option but surface verification failures clearly.

## Definition of done

- `--comment-mode graph` passes all existing Graph tests and still sends the supplied token.
- `--comment-mode ui` starts without `account/page.txt`, never calls `resolve_page_id`, and passes `access_token=None` to the commenter.
- Playwright switches to the configured Page, submits one comment through the browser, and returns success only after a verifiable post-submit state.
- Invalid targets, expired cookies, missing Page identity, and missing composer produce safe errors without token/cookie leakage.
- Tests and Python compile checks pass.

## Unresolved questions

- Which Facebook locale(s) must be supported for Page-switch and submit labels beyond English/Vietnamese?
- Should UI mode require headed Chromium by policy, or allow `--headless` for CI/manual automation?
