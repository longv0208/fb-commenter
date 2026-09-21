# Facebook Fanpage Commenter CLI

Công cụ comment Fanpage Facebook qua CLI (dùng Chrome + cookie)

## Cài đặt

```bash
cd tools/fb-commenter
pip install -r requirements.txt
playwright install chromium
```

## Cách dùng

```bash
python main.py \
  --urls 1234567890_9876543210,1234567890_9876543211 \
  --cookies cookies.txt \
  --comment-list comments.txt \
  --page-id 1234567890 \
  --page-token account/page.txt \
  --proxy http://user:pass@proxy-ip:port \
  --delay-min 1 \
  --delay-max 60 \
  --threads 3 \
  --headless
```

## File cần có

- `cookies.txt` (mỗi dòng 1 cookie)
- `comment_list.txt` (mỗi dòng 1 comment)
- `account/page.txt` (Page Access Token, không commit hoặc in ra log)

## Lưu ý quan trọng

- `--urls` phải là Page post object ID dạng `page_id_post_id`, hoặc URL bài viết hỗ trợ được chuyển về dạng này. Page/user ID đơn lẻ và `pfbid...` bị từ chối.
- `--page-id` là tùy chọn nếu token hợp lệ có thể tự phân giải ID. Thứ tự ưu tiên là `--page-id` → `account/page_id.txt` → `GET /v26.0/me?fields=id`; resolver gửi token bằng header `Authorization: Bearer` và chỉ nhận ID dạng số. Lỗi HTTP, JSON hoặc kết nối dừng trước khi mở trình duyệt với thông báo tổng quát.
- Page Access Token phải thuộc đúng Page, còn hạn, và có quyền bình luận cần thiết (thường `pages_manage_engagement` cùng tác vụ `MODERATE`).
- HTTP 400 thường do target không tồn tại/không truy cập được, sai Page ID, token sai Page/quyền, hoặc post không dùng được với Graph API. Lỗi được ghi ở dạng status/code/message đã giới hạn; token/cookie không được ghi.
- Ctrl+C dừng an toàn, đóng context/browser/Playwright và thoát với mã 130.
- Proxy rất quan trọng để tránh block; không đặt thông tin xác thực proxy trong log.
- Delay 1-60 phút là ngẫu nhiên. `--threads` hiện chỉ giữ tương thích CLI và chưa chạy song song.