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
  --urls 1234567890,9876543210 \
  --cookies cookies.txt \
  --comment-list comments.txt \
  --page-id 1234567890 \
  --proxy http://user:pass@proxy-ip:port \
  --delay-min 1 \
  --delay-max 60 \
  --threads 3 \
  --headless
```

## File cần có

- `cookies.txt` (mỗi dòng 1 cookie)
- `comment_list.txt` (mỗi dòng 1 comment)

## Lưu ý quan trọng

- Cần Page Access Token của Fanpage (user sẽ cung cấp)
- Proxy rất quan trọng để tránh block
- Delay 1-60 phút là ngẫu nhiên