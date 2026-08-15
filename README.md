# Invoice Parser

An intelligent invoice extraction module for Frappe using local deep learning OCR (Doctr/PaddleOCR) with Gemini AI fallback.

## Installation

When installing on another Frappe instance, simply run:

```bash
bench get-app https://github.com/yourusername/invoice_parser
bench install-app invoice_parser
```

### Docker Development Note

If you are using `frappe_docker` and encounter `ModuleNotFoundError: No module named 'invoice_parser'` in background queues after installation, it means the python environment inside your background worker containers didn't sync the editable package properly.

Run this inside your backend/queue containers to fix the python path:
```bash
env/bin/pip install -e apps/invoice_parser
# or just symlink it
ln -s /home/frappe/frappe-bench/apps/invoice_parser/invoice_parser /home/frappe/frappe-bench/env/lib/python3.14/site-packages/invoice_parser
```

## Features
- Background extraction via Python (`invoice2data`)
- Fuzzy match items and parties against ERPNext masters
- Gemini AI fallback
- Realtime progress updates in the UI
