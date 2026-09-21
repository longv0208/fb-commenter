---
title: "Tự động lấy Facebook Page ID từ Page Access Token"
description: "Cho phép CLI suy ra Page ID qua Graph API khi page_id.txt và --page-id đều chưa có."
status: completed
priority: P1
effort: 2h
branch: main
tags: [cli, facebook, graph-api, page-access-token]
created: 2026-09-21
---

# Mục tiêu

Loại bỏ lỗi CLI yêu cầu cấu hình Facebook Page ID trong trường hợp Page Access Token đã có ở `account/page.txt`. Không thay đổi luồng comment, cookie login, hay định dạng post ID.

# Phạm vi tối thiểu

- Chỉ `main.py` chịu trách nhiệm gọi Graph API và bổ sung giá trị `args.page_id` trước khi dựng `FacebookFanpageCommenter`.
- Dùng `GET https://graph.facebook.com/v26.0/me?fields=id` với Page Access Token đọc từ dòng không trống đầu tiên của `account/page.txt`.
- Giữ timeout 30 giây, proxy tùy chọn, HTTPS, và lỗi CLI không chứa token.
- Nếu `--page-id` hoặc `account/page_id.txt` có giá trị, ưu tiên giá trị đó; không gọi `/me`.
- Không ghi Page ID suy ra xuống `account/page_id.txt` trong bản thay đổi tối thiểu.

# Luồng xử lý

1. Resolve các file mặc định theo thư mục dự án.
2. Đọc và kiểm tra Page Access Token trước khi khởi tạo browser.
3. Resolve Page ID theo thứ tự `--page-id` → `account/page_id.txt` → Graph API `/v26.0/me`.
4. Kiểm tra response thành công và JSON có `id`; chuyển thành chuỗi đã strip.
5. Truyền Page ID và token vào `FacebookFanpageCommenter`.
6. Giữ nguyên validation `<page_id>_<post_id>` hiện có.

# Các phase

## Phase 1 — CLI resolver (`main.py`)

- Giữ `GRAPH_API_VERSION = "v26.0"` làm nguồn version duy nhất.
- Tách hoặc giữ helper async `resolve_page_id(access_token, proxy=None)` trong `main.py`.
- Dùng `httpx.AsyncClient(timeout=30.0, follow_redirects=True)` và thêm `proxy` chỉ khi được cấu hình.
- Gửi `fields=id` và access token; không log URL/request/credential.
- Với HTTP lỗi, JSON không hợp lệ, hoặc thiếu `id`, trả lỗi tổng quát an toàn; không đưa response body/token vào thông báo.
- Chỉ gọi helper khi `args.page_id` vẫn rỗng sau khi đọc `account/page_id.txt`.
- Bảo đảm `access_token` được truyền vào constructor; không dùng placeholder token.

## Phase 2 — Tests

- Bổ sung test async cho resolver thành công, kiểm tra endpoint/version, `fields=id`, token và proxy.
- Bổ sung test cho HTTP non-2xx và response thiếu `id`.
- Bổ sung test CLI fallback: thiếu `page_id.txt` vẫn đi tiếp nếu resolver thành công; có Page ID cấu hình thì không gọi resolver.
- Kiểm tra lỗi không làm lộ token hoặc response body nhạy cảm.
- Không gọi Facebook thật trong unit test; live verification chỉ thực hiện thủ công với Page được ủy quyền.

## Phase 3 — Documentation

- `docs/runtime-usage.md`: mô tả Page ID có thể lấy từ `--page-id`, `account/page_id.txt`, hoặc tự suy ra từ `account/page.txt`; nêu lỗi token invalid/không phải Page token.
- `docs/system-architecture.md`: ghi rõ nhánh `/me?fields=id` trước khi tạo commenter.
- Nếu triển khai thay đổi, thêm entry ngắn vào `docs/project-changelog.md`.

# Files liên quan

- Sửa: `main.py`
- Test: `tests/test_main.py` hoặc test module hiện hữu
- Tài liệu: `docs/runtime-usage.md`, `docs/system-architecture.md`, tùy chọn `docs/project-changelog.md`
- Không sửa: `facebook_fanpage_commenter.py`, `cli.py`, `config.py`

# Tiêu chí hoàn thành

- Chạy CLI với `account/page.txt` và không có `account/page_id.txt` không còn dừng vì thiếu Page ID; resolver được gọi trước browser startup.
- Page ID trả về được dùng cho validation post object ID.
- Sai/hết hạn token cho lỗi rõ ràng nhưng không lộ secret.
- Existing tests và resolver tests pass.
- Không có request live trong test suite; không ghi token vào file/log.

# Rủi ro và giảm thiểu

- Token user có thể là User Access Token hoặc token không thuộc Page: kiểm tra `id` và báo lỗi; không tự đoán Page khác.
- `/me` có thể bị proxy/network timeout: dùng timeout hữu hạn và giữ lỗi an toàn.
- Page ID CLI/file sai vẫn được ưu tiên theo hợp đồng hiện tại: không âm thầm ghi đè; Graph API comment sẽ trả lỗi nếu ID không khớp.
- Graph API version thay đổi: dùng constant và test endpoint để tránh hard-code rải rác.

# Unresolved questions

- Có cần persist Page ID suy ra vào `account/page_id.txt` cho các lần chạy sau không? Đề xuất: chưa cần để giữ thay đổi tối thiểu.
- Có muốn dùng Authorization header thay vì query parameter cho token để giảm nguy cơ URL leakage không? Đề xuất: quyết định theo API convention hiện tại; nếu đổi, cập nhật test và tài liệu.
