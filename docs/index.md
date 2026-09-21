# Facebook Fanpage Commenter Documentation

This documentation describes the current `main.py` runtime for the Facebook Fanpage Commenter CLI. It is intentionally conservative: production use requires valid Facebook credentials and a controlled test page.

## Contents

- [Runtime usage](./runtime-usage.md) - installation, required inputs, canonical post IDs, and shutdown behavior.
- [System architecture](./system-architecture.md) - runtime flow and component responsibilities.
- [Code standards](./code-standards.md) - structure, safety, and maintenance conventions.
- [Project overview and PDR](./project-overview-pdr.md) - scope, requirements, and acceptance criteria.
- [Development roadmap](./development-roadmap.md) - current status and follow-up work.
- [Project changelog](./project-changelog.md) - documentation and runtime-fix history.
- [Codebase summary](./codebase-summary.md) - source-verified structure and runtime behavior summary.

## Canonical entry point

Run `python main.py`. The separate `cli.py` module contains an older interactive argument parser and is not the runtime entry point documented here.

## Security reminder

Treat Page Access Tokens, Facebook cookies, proxy credentials, and log files as secrets. Keep them outside source control, do not paste their values into issue reports, and rotate them if exposed.
