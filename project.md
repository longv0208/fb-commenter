# Facebook Fanpage Commenter Project

## Tóm tắt
Công cụ CLI Python comment Fanpage Facebook (dùng Chrome + cookie).

## Cấu trúc
```
tools/fb-commenter/
├── main.py
├── cli.py
├── facebook_fanpage_commenter.py
├── config.py
├── cookies.txt
├── comment_list.txt
├── requirements.txt
├── tests/
│   └── test_fanpage_commenter.py
└── README.md
```

## Cách chạy
```bash
cd tools/fb-commenter
pip install -r requirements.txt
playwright install chromium
python main.py --help
```

## Lưu ý quan trọng
- Cần Page Access Token của Fanpage
- Proxy rất quan trọng
- File cookies.txt và comment_list.txt là bắt buộc