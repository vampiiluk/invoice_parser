# Invoice Parser

An intelligent invoice extraction app for Frappe/ERPNext. It reads invoice PDFs
with local deep-learning OCR, extracts structured fields and line items, and
pushes them straight into ERPNext as Purchase Invoices and Items — with a
Gemini AI fallback when OCR alone is not enough.

## Highlights

- **Multi-reader OCR cascade:** extraction tries a configurable chain of input
  readers — `pdfium`, `doctr`, `gvision` (Google Vision), `pdfplumber` — in
  priority order. You pick the order in Settings.
- **invoice2data-based extraction:** battle-tested template engine with
  per-issuer regex templates, keyword matching, and `Invoice Template` records
  managed right inside Frappe (created, edited and synced as `.yml` files).
- **Gemini AI fallback:** when OCR fails, the app calls Gemini to generate an
  extraction template from the raw text, saves it as an `Invoice Template`, and
  retries — so the same issuer only needs AI help once.
- **Direct API fallback:** a second AI path returns the structured payload
  directly (JSON) when template generation is disabled or misses.
- **Fuzzy matching against ERPNext:** extracted companies/parties are matched
  against Suppliers and Customers, and extracted line items against Item
  masters, using fuzzy ratio thresholds — with a manual confirm step.
- **One-click item creation:** turn any unmatched extracted line into a real
  ERPNext Item (optionally with a set default UOM / item group), or bulk-create
  all unmatched rows at once.
- **Purchase Invoice creation:** generate a Purchase Invoice from the parsed
  data, with extracted lines matched to items, quantities and rates; existing
  references are respected so you don't get duplicates.
- **Template learning:** AI-built templates are stored as `Invoice Template`
  doctypes with case-insensitive keywords and non-strict required fields, so
  partial matches still succeed.
- **Realtime progress:** `invoice_parsed` / `invoice_parse_failed` events push
  progress to the UI while extraction runs in the background queue.
- **Strict rule injection:** AI regex guidance is engineered for real-world
  invoices — tolerant of newlines, thousands separators, currency symbols and
  multi-line table rows — so generated templates match reliably.
- **OCR geometry data:** doctr results are saved as JSON geometry on the
  document for downstream inspection and layout-aware processing.

## Doctypes

| Doctype | Purpose |
|---|---|
| `Invoice Parser List` | One document per invoice file: status, extracted company/party, invoice number, date, totals, and the parsed line items |
| `Invoice Parse Item` | A single extracted line: description, matched Item, qty, rate, amount, UOM, item group |
| `Invoice Template` | Per-issuer extraction template (YAML content managed in Frappe) |
| `Invoice Parser Settings` | OCR cascade order, Gemini fallback toggle/key/model, default Item Group & UOM, allowed item groups, templates directory |
| `Extraction Cascade Item` | Ordered list of input readers to try |
| `Invoice Parser Allowed Item Group` | Restricts which item groups items can be created under |

## Installation

```bash
bench get-app https://github.com/vampiiluk/invoice_parser
bench install-app invoice_parser
```

### Docker Development Note

If you use `frappe_docker` and hit `ModuleNotFoundError: No module named
'invoice_parser'` in background queues after install, the queue containers did
not sync the editable package. Fix the python path inside the backend/queue
containers:

```bash
env/bin/pip install -e apps/invoice_parser
# or just symlink it
ln -s /home/frappe/frappe-bench/apps/invoice_parser/invoice_parser /home/frappe/frappe-bench/env/lib/python3.14/site-packages/invoice_parser
```

## Dependencies

- `invoice2data[doctr,ai,pdfplumber,googlevision]` — extraction engine + readers
- `thefuzz` — fuzzy matching against ERPNext masters
- `google-genai` — Gemini fallback and template generation
- Frappe `>=16.0.0,<17.0.0`
