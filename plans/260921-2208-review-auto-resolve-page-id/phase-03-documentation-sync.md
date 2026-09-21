# Phase 3 — Documentation sync

## Context links

- `README.md`
- `docs/runtime-usage.md`
- `docs/system-architecture.md`
- `docs/project-overview-pdr.md`
- `docs/project-changelog.md`
- `docs/development-roadmap.md`

## Overview

- Priority: P2
- Status: pending
- Goal: make operator instructions match the actual auto-resolve behavior and file layout.

## Implementation steps

1. Update README usage so `--page-id` is optional when a valid Page Access Token can resolve it.
2. Explain precedence, `/v26.0/me?fields=id`, numeric-ID requirement, and failure before browser startup.
3. Update PDR acceptance criteria and operational checklist to allow auto-resolve while retaining explicit-ID verification.
4. Reconcile runtime/system docs with the final resolver error and validation behavior; avoid duplicate or contradictory statements.
5. Clarify that the resolved Page ID is not persisted and that a User Access Token/expired token is invalid for this flow.
6. Verify default paths: `main.py` currently derives `account/` and `comments/` from `base_dir.parents[1]`; document the required project layout or add an explicit fallback only after confirmation.
7. Add one changelog entry only for the final implementation, not for test-only iterations.

## Todo list

- [ ] Sync README and PDR.
- [ ] Confirm default path contract with project owner.
- [ ] Remove stale wording that says Page ID is always required.
- [ ] Keep all examples credential-free.

## Success criteria

- A new operator can run with only a valid token file plus canonical post IDs.
- Docs state when explicit Page ID is still preferred and how failures surface.
- No documentation suggests token persistence, live credentials, or unsupported post IDs.
