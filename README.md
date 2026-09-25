# Facebook Fanpage Commenter

Comment Facebook bằng cookie, dưới danh tính Page. Trình duyệt là Chrome cài trên máy, mở qua Playwright. Không dùng Graph API.

Có hai cách chạy:

- `python main.py` comment lần lượt các UID trong `list UID/UID.txt`.
- `python main.py campaign <tên>` tự vào các group, lướt feed, lọc bài, rồi comment.

## Cài đặt

Cần Python 3.12 và Chrome đã cài trên máy.

```powershell
cd "E:\Telegram Desktop\tool cmt\tools\fb-commenter"
pip install -r requirements.txt
python -m playwright install
```

Máy này đang dùng Python tại `C:\Users\FPTSHOP\AppData\Local\Temp\invpw-venv\Scripts\python.exe`. Lệnh bên dưới viết tắt là `python`.

## Dữ liệu nằm ngoài git

Repo git chỉ là `tools/fb-commenter`. Cookie, comment, UID, proxy và campaign nằm ở thư mục cha `tool cmt`, không được đẩy lên git.

```text
tool cmt/
├── account/
│   ├── account list.txt
│   ├── page.txt
│   ├── proxy.txt
│   ├── hidden-authors.txt
│   └── campaigns/
│       └── fpt_courses.json
├── comments/
│   └── comment list.txt
├── list UID/
│   └── UID.txt
└── tools/
    └── fb-commenter/
```

- `account/account list.txt`: cookie có `c_user` và `xs`.
- `account/page.txt`: Page ID dạng số. Tool mở trang Page và bấm **Chuyển ngay**.
- `account/proxy.txt`: một dòng proxy, dạng `http://user:pass@host:port`. Lệnh UID bắt buộc có proxy. Campaign có thể thêm `--no-proxy`.
- `comments/comment list.txt`: mỗi dòng một câu. Mỗi bài lấy một câu chưa dùng trong lượt đó.
- `list UID/UID.txt`: mỗi dòng một UID hoặc link bài. Chỉ dùng cho `python main.py`.
- `account/hidden-authors.txt`: mỗi dòng một UID người đăng. Campaign bỏ bài của các UID này và bài do chính Page đăng.
- `account/campaigns/<tên>.json`: danh sách group và điều kiện lọc. Mẫu ở `config/campaign.example.json`.

## Comment theo UID

```powershell
python main.py
```

Mỗi UID một câu. Giữa hai comment chờ ngẫu nhiên 1 đến 60 phút. Bài lỗi thì bỏ qua, không chờ, và câu đó còn lại cho lần sau. Cookie sai thì dừng cả lượt.

Một bài, không chờ:

```powershell
python main.py --urls 1610321213811556 --delay-min 0 --delay-max 0
```

`--verbose` in chi tiết. `--headless` không hiện cửa sổ Chrome.

## Quét group rồi comment

Thêm link group vào `groups` trong `account/campaigns/fpt_courses.json`. Một lượt đi lần lượt hết các group trong file, cùng một cửa sổ Chrome.

```powershell
python main.py campaign fpt_courses --no-proxy --verbose
```

Các bước:

1. Mở Chrome và đăng nhập bằng cookie.
2. Vào Page, bấm **Chuyển ngay**.
3. Vào group. Feed mặc định là **Hoạt động mới đây**. Tool bấm dòng đó và chọn **Bài viết mới**.
4. Lướt feed. Mỗi lần khoảng một màn hình, rồi chờ `scroll_pause_ms`. Dừng group khi đủ `max_scrolls`, hoặc khi `empty_scroll_limit` lần liên tiếp không thấy bài mới.
5. Giữ bài có mã trong `subjects` hoặc cụm trong `help_phrases`. So khớp không phân biệt hoa thường và dấu. `MAD` cũng khớp `MAD101`.
6. Bỏ bài không có chữ, bài của Page, bài của UID trong `hidden-authors.txt`, và bài đã comment thành công.
7. Gửi một câu trong `comment list.txt`. Chỉ tính thành công khi đúng câu đó hiện trên bài.

Với cấu hình hiện tại, mỗi group lướt tối đa 20 lần, mỗi lần chờ 1,5 giây. Phần lướt khoảng 30 giây nếu feed còn bài mới. Cả lượt còn cộng thời gian đăng nhập và chuyển Page.

Giới hạn trong file JSON:

- `max_comments_per_group`: 5
- `max_comments_per_run`: 15
- `cooldown_seconds`: 120 giây giữa hai comment campaign

Xem bài sẽ comment, chưa gửi:

```powershell
python main.py campaign fpt_courses --dry-run --no-proxy
```

`use_jev` mặc định là `false`: bài khớp từ khóa được comment luôn. Đặt `true` thì cần biến môi trường `JEV_API_KEY`. Jev trả nhãn `comment` với độ tin cậy từ `jev_confidence` thì mới gửi. Lỗi Jev thì bỏ bài đó.

Lịch sử nằm ở `tools/fb-commenter/data/app.db`. Bài đã gửi thành công không bị gửi lại.

## Kiểm tra

```powershell
python -m pytest tests -q
```
