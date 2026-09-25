# Facebook Fanpage Commenter

Công cụ comment Facebook bằng cookie, dưới danh tính Page. Trình duyệt là Chrome cài trên máy, mở qua Playwright. Không dùng Graph API.

## Chạy

Cần Python 3.12.

```bash
cd tools/fb-commenter
pip install -r requirements.txt
python -m playwright install
python main.py
```

## Dữ liệu nằm ngoài git

Repo git chỉ là thư mục `tools/fb-commenter`. Ba thư mục dữ liệu nằm cạnh `tools`, tức là thư mục cha `tool cmt`. Đẩy repo lên git không kèm các thư mục đó. Máy mới phải tự tạo lại:

```text
tool cmt/
├── account/
│   ├── account list.txt
│   ├── page.txt
│   └── proxy.txt
├── comments/
│   └── comment list.txt
├── list UID/
│   └── UID.txt
└── tools/
    └── fb-commenter/    ← repo git
```

Lệnh `python main.py` tự đọc các file đó:

- `list UID/UID.txt`: mỗi dòng một UID bài viết
- `comments/comment list.txt`: mỗi dòng một câu comment
- `account/account list.txt`: cookie Facebook, có `c_user` và `xs`
- `account/page.txt`: Page ID dạng số, dùng để bấm chuyển sang Page
- `account/proxy.txt`: một dòng proxy, ví dụ `http://user:pass@host:port`
- `account/hidden-authors.txt`: mỗi dòng một UID người đăng cần bỏ qua
- `account/campaigns/<tên>.json`: danh sách group và mã môn. Mẫu nằm ở `config/campaign.example.json`

Quét group rồi comment:

```bash
python main.py campaign fpt_courses --dry-run
python main.py campaign fpt_courses
```

Dry-run chỉ quét và lọc, không gửi. Lượt gửi thật cần biến môi trường `JEV_API_KEY`. Bài khớp mã môn hoặc câu xin hỗ trợ mới được Jev gắn nhãn. Nhãn `comment` với độ tin cậy từ `0.8` mới được gửi. Nghỉ giữa các comment của campaign là `cooldown_seconds` trong file JSON, mặc định 120 giây. Lệnh `python main.py` không campaign vẫn đi `UID.txt` và delay 1–60 phút.

Mỗi bài trong `UID.txt` nhận một câu chưa dùng. Giữa các comment, chương trình chờ ngẫu nhiên từ 1 đến 60 phút. Proxy được gắn vào trình duyệt lúc mở. Không có proxy thì trình duyệt không mở.

Muốn xem từng bước:

```bash
python main.py --verbose
```

Muốn chạy không hiện cửa sổ:

```bash
python main.py --headless
```

Muốn comment vài bài cụ thể, không đụng cả file UID:

```bash
python main.py --urls 1610321213811556,1110186588408179 --delay-min 0 --delay-max 0
```

## Cách comment

1. Mở Facebook bằng cookie.
2. Vào Page và bấm **Chuyển ngay** nếu chưa đứng ở Page.
3. Mở UID. Số thuần được mở thành `https://www.facebook.com/<uid>`.
4. Ghi đúng một lần vào ô bình luận rồi nhấn Enter.
5. Chỉ tính thành công khi đúng câu đó hiện trên bài.

## Kiểm tra

```bash
python -m pytest tests -q
```
