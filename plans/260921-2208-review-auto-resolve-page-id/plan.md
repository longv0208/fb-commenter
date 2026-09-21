---
title: "Rà soát và hardening auto-resolve Facebook Page ID"
description: "Bổ sung kiểm chứng resolver Page ID, test nhánh CLI còn thiếu và đồng bộ tài liệu vận hành."
status: pending
priority: P1
effort: 3h
branch: main
tags: [cli, facebook, graph-api, page-id, tests, documentation]
created: 2026-09-21
---

# Mục tiêu

Làm cho luồng tự lấy Facebook Page ID từ Page Access Token ổn định, an toàn và có test hồi quy; không thay đổi luồng comment hoặc gọi Facebook thật trong test.

# Hiện trạng đã xác nhận

- `main.py` đã gọi `GET /v26.0/me?fields=id` khi thiếu `--page-id` và `account/page_id.txt`.
- Thứ tự ưu tiên hiện tại: CLI, file Page ID, Graph API; token đọc từ dòng không trống đầu tiên.
- `tests/test_main.py` đã có 4 test resolver cơ bản; toàn bộ suite hiện tại: 9 passed.
- Resolver mới kiểm tra `id` truthy, chưa ràng buộc ID dạng số; chưa có test nhánh CLI precedence/fallback, lỗi transport/timeout, hoặc ID sai kiểu.
- Runtime/system/changelog/roadmap đã đề cập auto-resolve; README và PDR/checklist còn cần đồng bộ.

# Phases

1. [Phase 1 — Resolver contract](phase-01-resolver-contract.md): harden validation/error boundary, giữ timeout/proxy/version và thứ tự ưu tiên.
2. [Phase 2 — Regression tests](phase-02-regression-tests.md): bổ sung test payload, network, CLI fallback/precedence và secret handling.
3. [Phase 3 — Documentation sync](phase-03-documentation-sync.md): cập nhật README/PDR/checklist và xác nhận đường dẫn file mặc định.
4. [Phase 4 — Verification](phase-04-verification.md): chạy test/compile, kiểm tra không có request live hoặc credential trong artefact.

# Files liên quan

- Sửa dự kiến: `main.py`, `tests/test_main.py`, `README.md`, `docs/project-overview-pdr.md`, có thể `docs/runtime-usage.md`, `docs/system-architecture.md`, `docs/project-changelog.md`, `docs/development-roadmap.md`.
- Không sửa trong phạm vi: `facebook_fanpage_commenter.py`, `cli.py`, `config.py`.

# Tiêu chí hoàn thành

- Chỉ nhận Page ID số, lỗi token/response/network an toàn và không lộ secret.
- Có test chứng minh resolver chỉ chạy khi thiếu Page ID; Page ID cấu hình được ưu tiên.
- Test suite và compile pass; không có Facebook request thật.
- Tài liệu mô tả đúng fallback, điều kiện Page Access Token, không persist ID tự suy ra.

# Unresolved questions

- Có đổi token từ query parameter sang Authorization header không? Chỉ đổi nếu xác nhận tương thích Graph API và cập nhật test/docs.
- Có persist Page ID tự suy ra vào `account/page_id.txt` không? Mặc định chưa làm để giữ thay đổi tối thiểu.
- `base_dir.parents[1]` là layout bắt buộc của project hay cần hỗ trợ fallback khi chạy standalone `tools/fb-commenter`? Cần xác nhận trước khi đổi đường dẫn.
