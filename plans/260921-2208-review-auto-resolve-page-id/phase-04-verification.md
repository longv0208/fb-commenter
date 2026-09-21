# Phase 4 — Verification

## Context links

- `requirements.txt`
- `tests/`
- `main.py`

## Overview

- Priority: P1
- Status: pending
- Goal: verify the final change is compilable, tested, and secret-safe.

## Implementation steps

1. Run `python -m pytest -q` from `tools/fb-commenter`.
2. Run `python -m py_compile main.py facebook_fanpage_commenter.py tests/test_main.py tests/test_fanpage_commenter.py`.
3. Run `python main.py --help` to verify CLI startup does not require credentials.
4. Review test output and source for live Facebook calls, committed tokens, or proxy credentials.
5. If tests fail, fix implementation/test contract and rerun the suite; do not weaken assertions or add fake production shortcuts.
6. Record final test count and any manual controlled-Page verification separately from unit-test results.

## Todo list

- [ ] Run unit suite.
- [ ] Run compile check.
- [ ] Run help smoke test.
- [ ] Perform secret scan of changed files.
- [ ] Record unresolved production verification requirements.

## Success criteria

- Tests, compile, and help smoke test pass.
- No live network dependency exists in CI/unit tests.
- Documentation and code agree on resolver behavior.
