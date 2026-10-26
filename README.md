# Facebook Fanpage Commenter

Comment Facebook bằng cookie, dưới danh tính Page. Trình duyệt là Chrome cài trên máy, mở qua Playwright. Không dùng Graph API.

Có hai cách chạy:

- `python main.py` comment lần lượt các UID trong `list UID/UID.txt`.
- `python main.py campaign <tên>` tự vào các group, lướt feed, lọc bài, rồi comment.

## Cài đặt

Cần Python 3.10+ và Chrome đã cài trên máy. **Repo dùng Git LFS** cho `model.safetensors` (~515MB) — cần `git lfs` trước khi clone, hoặc `git lfs pull` sau khi clone, nếu không file model chỉ là pointer text và PhoBERT filter không load được.

```powershell
git lfs install          # một lần duy nhất trên máy
git clone <repo>         # LFS tự pull nếu đã install; nếu clone rồi: git lfs pull
cd "E:\Telegram Desktop\tool cmt\tools\fb-commenter"

# venv (khuyến nghị — PhoBERT cần torch ~4GB)
python -m venv .venv && .venv\Scripts\pip install -r requirements.txt
# PhoBERT (chỉ khi dùng use_phobert): torch + transformers + sentencepiece
.venv\Scripts\pip install torch transformers==4.46.3 tokenizers==0.20.3 accelerate==1.1.1 sentencepiece
python -m playwright install
```

Máy này đang dùng venv tại `E:\venv-cmt\Scripts\python.exe` (torch 2.5.1+cu121 + transformers 4.46.3). Lệnh bên dưới viết tắt là `python`.

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
5. Bấm **Xem thêm** trên các bài đang hiện, rồi mới đọc chữ. Bài ngắn vẫn được đọc. Bài chỉ có ảnh được chụp và đọc chữ trên ảnh. Giữ bài có mã trong `subjects` hoặc cụm trong `help_phrases`. So khớp không phân biệt hoa thường và dấu. `MAD` cũng khớp `MAD101`.
6. Bỏ bài không có chữ, bài của Page, bài của UID trong `hidden-authors.txt`, và bài đã comment thành công.
7. Gửi một câu trong `comment list.txt`. Chỉ tính thành công khi đúng câu đó hiện trên bài. Bài khóa comment được ghi nhớ và các lượt sau không mở lại.

Với cấu hình hiện tại, mỗi group lướt tối đa 20 lần, mỗi lần chờ 1,5 giây. Phần lướt khoảng 30 giây nếu feed còn bài mới. Cả lượt còn cộng thời gian đăng nhập và chuyển Page.

Giới hạn trong file JSON:

- `max_comments_per_group`: 5
- `max_comments_per_run`: 15
- `cooldown_seconds`: 120 giây giữa hai comment campaign

Xem bài sẽ comment, chưa gửi:

```powershell
python main.py campaign fpt_courses --dry-run --no-proxy
```

Lọc ngữ nghĩa hai tầng sau `keyword_match`, đặt trong campaign JSON:

- `use_phobert: true` → sau khi bài khớp keyword, PhoBERT (local, `models/phobert-filter/`, đã fine-tune trên ~1300 mẫu) chấm `P(true)`; `>= phobert_threshold` (mặc định 0.8) mới comment. Cần torch + transformers trong venv; GPU nhanh hơn nhưng CPU vẫn chạy.
- `phobert_review_all: true` → PhoBERT duyệt cả bài không khớp keyword.
- Tương thích cũ: `use_jev`/`jev_confidence`/`jev_review_all` được đọc như `use_phobert`/`phobert_threshold`/`phobert_review_all` khi key mới chưa có.

Jev (LLM API bên ngoài, `jev_client.py`) vẫn còn trong repo nhưng không được gọi trong run path. `JEV_API_KEY` đọc từ biến môi trường hoặc settings DB (điền qua màn Cài đặt/API) — chỉ dùng nếu wire lại Jev.

Lịch sử nằm ở `tools/fb-commenter/data/app.db`. Bài đã gửi thành công không bị gửi lại.

## Kiểm tra

```powershell
python -m pytest tests -q
```

## Desktop GUI (Electron)

Tool có giao diện desktop trong `desktop/` — Electron shell gọi backend Python
qua HTTP/WebSocket (`127.0.0.1:8787`). Backend: `backend/server.py` (aiohttp).

### Chạy dev

```powershell
# terminal 1: backend
python -m backend.server --port 8787

# terminal 2: electron (EXTERNAL_BACKEND=1 để không spawn backend mới)
cd desktop
npm install
npm run dev     # hoặc: npm start (tự spawn backend)
```

### Đóng gói .exe

```powershell
# build backend -> backend-dist\server\server.exe (cần pyinstaller)
powershell -File desktop\build-backend.ps1

# build electron -> desktop\dist\
cd desktop && npm run dist
```

### Tính năng GUI

- Dashboard: danh sách account + trạng thái + start/stop nhanh.
- Tài khoản: thêm/sửa/xóa (cookie, page id, proxy, profile dir persistent).
- Chạy: chọn nhiều account, mode UID/Campaign, delay, headless, dry-run, không proxy.
- Campaign: editor đầy đủ cho JSON campaign — groups, subjects, help_phrases, mọi tham số scroll/giới hạn, và bộ lọc PhoBERT (`use_phobert`, threshold, review_all). Legacy `use_jev`/`jev_*` được dịch sang `phobert_*` khi load và ghi lại sạch khi save.
- Logs: stream real-time theo account, lọc level, tìm kiếm, export `.log`.
- Cài đặt: data root, delay mặc định (JEV key field đã bỏ — Jev không còn dùng).

Mỗi account chạy song song mở 1 cửa sổ Chrome riêng (proxy + profile riêng).
Cookie của account lưu trong `data/app.db` (plaintext — chỉ dùng local).
