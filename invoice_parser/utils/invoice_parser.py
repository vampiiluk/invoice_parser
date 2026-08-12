import os
import json
import frappe
from invoice2data import extract_data

# ================= GLOBAL MONKEY PATCHES =================
import yaml
from invoice2data.extract.invoice_template import InvoiceTemplate
from invoice2data.extract.parsers import lines
if not hasattr(lines, 'original_parse_by_rule'):
    lines.original_parse_by_rule = lines.parse_by_rule
    def patched_parse_by_rule(template, field, rule, content):
        if "line_separator" not in rule and "line_separator" in template.get("lines", {}):
            rule["line_separator"] = template["lines"]["line_separator"]
        return lines.original_parse_by_rule(template, field, rule, content)
    lines.parse_by_rule = patched_parse_by_rule

if not hasattr(InvoiceTemplate, 'original_matches_input'):
    InvoiceTemplate.original_matches_input = InvoiceTemplate.matches_input
    def regex_matches_input(self, extracted_str: str) -> bool:
        import re
        for keyword in self.get("keywords", []):
            try:
                if not re.search(str(keyword), extracted_str, flags=re.IGNORECASE):
                    return False
            except Exception:
                if str(keyword).lower() not in extracted_str.lower():
                    return False
        for keyword in self.get("exclude_keywords", []):
            try:
                if re.search(str(keyword), extracted_str, flags=re.IGNORECASE):
                    return False
            except Exception:
                if str(keyword).lower() in extracted_str.lower():
                    return False
        return True
    InvoiceTemplate.matches_input = regex_matches_input
# =========================================================


@frappe.whitelist()
def enqueue_invoice_processing(docname, force_ai=0):
    # This is called by the client script when a new Invoice Parser List is saved with an attachment.
    frappe.db.set_value("Invoice Parser List", docname, "status", "Processing")
    frappe.enqueue(
        "invoice_parser.utils.invoice_parser.process_invoice",
        queue="long",
        timeout=1500,
        docname=docname,
        force_ai=int(force_ai)
    )

def process_invoice(docname, force_ai=0):
    doc = frappe.get_doc("Invoice Parser List", docname)
    try:
        extraction_logs = []
        def log(msg):
            extraction_logs.append(msg)
            frappe.logger().info(msg)
        # Update status
        doc.db_set("status", "Processing")

        if not doc.invoice_file:
            raise Exception("No invoice file attached.")

        # Get file path
        file_doc = frappe.get_doc("File", {"file_url": doc.invoice_file})
        file_path = frappe.get_site_path(file_doc.file_url.strip('/'))

        # Fetch cascade settings
        settings = frappe.get_doc("Invoice Parser Settings")
        
        # Enable Gemini if checked in settings
        if settings.enable_gemini_fallback:
            if settings.gemini_api_key:
                os.environ["INVOICE2DATA_AI_PROVIDER"] = "gemini"
                os.environ["INVOICE2DATA_AI_MODEL"] = settings.gemini_model or "gemini-3.1-flash-lite"
                os.environ["INVOICE2DATA_AI_API_KEY"] = settings.get_password("gemini_api_key") if settings.meta.get_field("gemini_api_key").fieldtype == "Password" else settings.gemini_api_key
        extracted_result = None
        
        # If no cascade is defined, fallback to pdfium -> doctr
        modules_to_try = []
        if settings.extraction_cascade:
            modules_to_try = [item.input_reader for item in sorted(settings.extraction_cascade, key=lambda x: x.priority)]
        else:
            modules_to_try = ["pdfium", "doctr"]

        import importlib
        from invoice2data.extract.loader import read_templates
        
        all_templates = read_templates()
        templates_dir = getattr(settings, "templates_directory", None)
        if templates_dir:
            if not templates_dir.startswith("/"):
                templates_dir = frappe.get_site_path(templates_dir)
            if os.path.exists(templates_dir):
                all_templates += read_templates(templates_dir)

        input_module = None
        if not force_ai:
            for module_name in modules_to_try:
                try:
                    log(f"Attempting extraction using {module_name}...")
                    if module_name in ["pdfium", "doctr"]:
                        input_module = importlib.import_module(f"invoice_parser.utils.{module_name}")
                    else:
                        input_module = importlib.import_module(f"invoice2data.input.{module_name}")
                    
                    # Intercept text extraction to append it to the UI log and capture OCR geometry
                    original_to_text = getattr(input_module, 'to_text', None)
                    if original_to_text:
                        def intercepted_to_text(path):
                            raw_text = ""
                            if module_name == "doctr":
                                try:
                                    from invoice_parser.utils.doctr import _get_model, _render
                                    from doctr.io import DocumentFile
                                    
                                    if path.lower().endswith(".pdf"):
                                        document = DocumentFile.from_pdf(path)
                                    else:
                                        document = DocumentFile.from_images(path)
                                    
                                    doctr_res = _get_model()(document)
                                    
                                    # Save the JSON geometry directly to the Doctype
                                    try:
                                        import json
                                        doc.ocr_geometry_data = json.dumps(doctr_res.export())
                                        doc.save(ignore_permissions=True)
                                    except Exception as json_e:
                                        log(f"Failed to save doctr JSON: {json_e}")
                                        
                                    raw_text = _render(doctr_res)
                                except Exception as e:
                                    log(f"Custom doctr extraction failed: {e}")
                                    raw_text = original_to_text(path)
                            else:
                                raw_text = original_to_text(path)
                                
                            try:
                                decoded = raw_text.decode('utf-8') if isinstance(raw_text, bytes) else str(raw_text)
                                log(f"--- RAW TEXT EXTRACTED BY {module_name.upper()} ---\n{decoded}\n-----------------------------------------")
                            except Exception as decode_e:
                                log(f"Failed to decode raw text for logging: {decode_e}")
                            return raw_text
                        input_module.to_text = intercepted_to_text
    
                    try:
                        result = extract_data(file_path, input_module=input_module, templates=all_templates)
                    finally:
                        if original_to_text:
                            input_module.to_text = original_to_text
                            
                    if result:
                        log(f"Extraction successful using {module_name}!")
                        extracted_result = result
                        break
                except Exception as e:
                    log(f"invoice2data extraction failed with {module_name}: {e}")
                    continue

        if extracted_result and not extracted_result.get("lines"):
            log("Extracted result is missing items/lines. Discarding result to force AI fallback.")
            extracted_result = None

        if not extracted_result and settings.enable_gemini_fallback:
            # Step 1: AI Template Generation
            if getattr(settings, 'generate_template_on_fallback', 0) and input_module:
                log("Attempting AI Template Generation...")
                try:
                    text = ''
                    try:
                        text = input_module.to_text(file_path)
                        if isinstance(text, bytes):
                            text = text.decode('utf-8')
                    except Exception as e:
                        log(f'Could not extract text for template generation: {e}')
                    
                    if text:
                        import yaml
                        import json
                        from google import genai
                        from google.genai import types
                        
                        api_key = os.environ.get('INVOICE2DATA_AI_API_KEY')
                        model_name = os.environ.get('INVOICE2DATA_AI_MODEL', 'gemini-3.1-flash-lite')
                        
                        if api_key:
                            client = genai.Client(api_key=api_key)
                            
                            system_instruction = (
                                "You write extraction templates for the invoice2data library. Given the text "
                                "of a sample invoice, return a JSON object with: 'issuer' (the company name), "
                                "'keywords' (1-3 short strings that uniquely identify this issuer's documents), "
                                "optional 'exclude_keywords', and 'fields' mapping canonical field names "
                                "(date, invoice_number, amount, amount_untaxed, amount_tax, vat, iban) to a "
                                "Python regular expression with exactly ONE capturing group around the value. "
                                "Base every regex on the literal text of THIS sample so it matches. Return "
                                "ONLY the JSON object."
                                " CRITICAL RULES FOR REGEX: "
                                "1. Make regexes extremely loose and tolerant of newlines by using \\s+ instead of exact spaces. "
                                "2. NEVER hardcode currency symbols like 'Rs', '₨', '$'. Always use \\D* or .*? to skip them! "
                                "3. ONLY output the JSON object for the exact invoice provided. DO NOT output a generic 'Vertex42' template unless the invoice is actually from Vertex42! "
                                "4. IMPORTANT: You MUST also generate a 'lines' object to extract child table line items. The 'lines' object must have: 'start' (a regex matching the table header), 'end' (a regex matching the table end), and 'line' (a regex with named groups like (?P<description>...), (?P<qty>...), (?P<price>...), (?P<amount>...)). CRITICAL: OCR often extracts table columns on separate lines (e.g. ItemName\\nQty\\nPrice). Because invoice2data tests the 'line' regex line-by-line by default, it will FAIL to match. Therefore, you MUST ALWAYS provide a 'line_separator' regex to chunk the text by row start! For example, if rows start with a letter, use '\\n(?=[A-Za-z]+)'. IF ROWS START WITH A NUMBER, DO NOT EVER USE '\\n(?=\\d+)' AS IT WILL ACCIDENTALLY SPLIT ON PRICES TOO! Instead, you MUST analyze the text and use a very specific lookahead, such as '\\n(?=\\d+\\n[A-Za-z])', to guarantee it only splits at the actual start of a row. This forces invoice2data to test your 'line' regex against the whole chunk (where '\\s+' easily matches the newlines between columns). Make your line regex VERY RELAXED (use .*? instead of \\d+ because items often have brackets like [123]!). "
                                "5. For all numerical amounts (prices, totals, qty), ALWAYS support optional thousands separators by using '[\\d,]+' instead of just '\\d+'. E.g. use '[\\d,]+\\.\\d{2}' to successfully match '1,234.56'."
                            )
                            
                            response = client.models.generate_content(
                                model=model_name,
                                contents=[text],
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    system_instruction=system_instruction
                                )
                            )
                            
                            template_dict = json.loads(response.text)
                            
                            if "issuer" not in template_dict:
                                template_dict["issuer"] = "unknown"
                            
                            if template_dict:
                                templates_dir = settings.templates_directory or "/home/frappe/frappe-bench/sites/erp.sananahmad.dpdns.org/private/files/invoice_templates"
                                if not templates_dir.startswith("/"):
                                    templates_dir = frappe.get_site_path(templates_dir)
                                if not os.path.exists(templates_dir):
                                    os.makedirs(templates_dir, exist_ok=True)
                                
                                template_dict.setdefault('keywords', [template_dict.get('issuer', 'unknown')])
                                template_dict.setdefault('exclude_keywords', [])
                                
                                # Force case-insensitivity on keywords to combat AI casing mistakes
                                if 'keywords' in template_dict:
                                    template_dict['keywords'] = [str(k).lower() for k in template_dict['keywords']]
                                
                                # Disable strict required fields so partial matches succeed
                                template_dict['required_fields'] = []
                                
                                # Force strict date matching if AI is greedy
                                if 'date' in template_dict.get('fields', {}):
                                    template_dict['fields']['date'] = template_dict['fields']['date'].replace('(.*)', '[\\s\\S]*?([a-zA-Z]+\\s+\\d{1,2},\\s+\\d{4}|\\d{1,2}/\\d{1,2}/\\d{4})')
                                
                                template_name = str(template_dict.get('issuer', 'unknown')).replace(' ', '_').lower()
                                template_dict.setdefault('template_name', template_name)
                                
                                yaml_content = yaml.dump(template_dict, default_flow_style=False)
                                if not frappe.db.exists("Invoice Template", template_name):
                                    new_tmpl = frappe.get_doc({
                                        "doctype": "Invoice Template",
                                        "template_name": template_name,
                                        "content": yaml_content
                                    })
                                    new_tmpl.insert(ignore_permissions=True)
                                else:
                                    existing_tmpl = frappe.get_doc("Invoice Template", template_name)
                                    existing_tmpl.content = yaml_content
                                    existing_tmpl.save(ignore_permissions=True)
                                frappe.db.commit()
                                new_template = InvoiceTemplate(template_dict)
                                result = extract_data(file_path, input_module=input_module, templates=all_templates + [new_template])
                                if result and result.get('lines'):
                                    log("Successfully generated and matched new template via AI!")
                                    extracted_result = result
                                else:
                                    if result:
                                        log("AI Template Generation produced a template, but it failed to match any child 'lines'. Discarding...")
                                    else:
                                        log("AI Template Generation produced a template, but it completely failed to match the invoice text. Discarding...")
                                        
                                        # Debug why it failed
                                        try:
                                            optimized_text = input_module.to_text(file_path).decode('utf-8') if isinstance(input_module.to_text(file_path), bytes) else str(input_module.to_text(file_path))
                                            import unicodedata
                                            optimized_text = unicodedata.normalize('NFKD', optimized_text).encode('ascii', 'ignore').decode('ascii')
                                            
                                            if not new_template.matches_input(optimized_text):
                                                log(f"-> DEBUG: Template 'keywords' failed to match the text. Expected: {new_template.get('keywords', [])}")
                                            else:
                                                extracted_fields = new_template.extract(optimized_text, file_path, input_module)
                                                if not extracted_fields:
                                                    log("-> DEBUG: Template matched keywords, but new_template.extract() completely failed.")
                                                else:
                                                    missing_required = []
                                                    for req in ['date', 'amount', 'invoice_number', 'issuer']:
                                                        if req not in extracted_fields:
                                                            missing_required.append(req)
                                                    if missing_required:
                                                        log(f"-> DEBUG: Template failed because it could not extract required fields: {', '.join(missing_required)}")
                                                        # Print the exact regex that failed
                                                        for mr in missing_required:
                                                            if mr in new_template.get('fields', {}):
                                                                log(f"   Regex for {mr} was: {new_template['fields'][mr]}")
                                        except Exception as dbg_err:
                                            log(f"-> DEBUG error: {dbg_err}")
                except Exception as e:
                    log(f'AI Template Generation failed: {e}')
            # Step 2: Direct API Fallback if template generator was off or failed
            if not extracted_result:
                log("Attempting Gemini Direct API Fallback...")
                try:
                    from google import genai
                    from google.genai import types
                    import mimetypes
                    
                    api_key = os.environ.get("INVOICE2DATA_AI_API_KEY")
                    model_name = os.environ.get("INVOICE2DATA_AI_MODEL", "gemini-3.1-flash-lite")
                    
                    if api_key:
                        client = genai.Client(api_key=api_key)
                        mime_type, _ = mimetypes.guess_type(file_path)
                        
                        if str(file_path).lower().endswith(".webp"):
                            mime_type = "image/webp"
                            
                        with open(file_path, "rb") as f:
                            file_data = f.read()
                            
                        prompt = "Extract the following information from the invoice: issuer (company name string), invoice_number (string), date (string), amount (float), lines (list of items with 'description' string, 'qty' float, 'price' float, 'amount' float). Return ONLY a valid JSON object."
                        
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[
                                types.Part.from_bytes(data=file_data, mime_type=mime_type or "image/jpeg"),
                                prompt
                            ],
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json"
                            )
                        )
                        import json
                        extracted_result = json.loads(response.text)
                        log("Successfully extracted data via Gemini Direct API!")
                except Exception as e:
                    log(f"Gemini fallback failed: {e}")

        if not extracted_result:
            raise Exception("All extraction methods failed to parse the invoice (No templates matched, and AI fallback failed or was disabled).")

        
        # Populate fields
        
        # Clean up any lists returned by rogue AI or regex engines
        for key in ["issuer", "invoice_number", "amount", "date"]:
            if isinstance(extracted_result.get(key), list) and len(extracted_result[key]) > 0:
                extracted_result[key] = extracted_result[key][0]

        doc.extracted_company_name = extracted_result.get("issuer", "")
        doc.invoice_number = extracted_result.get("invoice_number", "")
        if "date" in extracted_result and extracted_result["date"]:
            from dateutil.parser import parse as parse_date
            try:
                # Frappe expects dates in YYYY-MM-DD for MariaDB Date fields
                parsed_date = parse_date(str(extracted_result["date"]))
                doc.date = parsed_date.strftime("%Y-%m-%d")
            except Exception as e:
                frappe.logger().warning(f"Could not parse date {extracted_result['date']}: {e}")
                doc.date = None
        doc.total_amount = extracted_result.get("amount", 0)

        # Run Fuzzy Matching (importing from fuzzy_matcher.py)
        from invoice_parser.utils.fuzzy_matcher import match_party, match_item
        
        party_match = match_party(doc.extracted_company_name)
        if party_match and isinstance(party_match, dict):
            doc.party_type = party_match.get("doctype")
            doc.matched_party = party_match.get("name")
        elif party_match and isinstance(party_match, tuple):
            doc.party_type, doc.matched_party = party_match

        matched_lines = extracted_result.get("lines", [])
        
        doc.set("extracted_items", [])
        for line in matched_lines:
            matched_item_name = match_item(line.get("description") or line.get("name") or line.get("item") or "")
            doc.append("extracted_items", {
                "extracted_item_name": line.get("description") or line.get("name") or line.get("item") or "",
                "matched_item": matched_item_name,
                "quantity": float(str(line.get("qty", 1)).replace(",", "")) if line.get("qty") else 1,
                "rate": float(str(line.get("price", 0)).replace(",", "")) if line.get("price") else 0,
                "system_rate": float(str(line.get("system_rate", 0)).replace(",", "")) if line.get("system_rate") else 0,
                "amount": float(str(line.get("amount", 0)).replace(",", "")) if line.get("amount") else 0
            })

        doc.extraction_log = "\n".join(extraction_logs)
        doc.raw_extracted_data = frappe.as_json(extracted_result) if extracted_result else ""
        doc.db_set("status", "Pending Review")
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        frappe.publish_realtime("invoice_parsed", {"docname": docname})

    except Exception as e:
        frappe.log_error(title=f"Invoice Parse Failed {docname}", message=frappe.get_traceback())
        
        # Save logs even on failure!
        extraction_logs.append(f"\nFATAL ERROR: {e}")
        doc.extraction_log = "\n".join(extraction_logs)
        try:
            if 'extracted_result' in locals() and extracted_result:
                doc.raw_extracted_data = frappe.as_json(extracted_result)
        except Exception:
            pass
            
        doc.status = "Failed"
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.publish_realtime("invoice_parse_failed", {"docname": docname})


@frappe.whitelist()
def create_invoice_from_request(docname, target_doctype):
    doc = frappe.get_doc("Invoice Parser List", docname)
    
    if target_doctype == "Purchase Invoice" and getattr(doc, "purchase_invoice_ref", None):
        return doc.purchase_invoice_ref
    if target_doctype == "Sales Invoice" and getattr(doc, "sales_invoice_ref", None):
        return doc.sales_invoice_ref
        
    new_doc = frappe.new_doc(target_doctype)
    
    if target_doctype == "Purchase Invoice":
        if doc.party_type == "Supplier" and doc.matched_party:
            new_doc.supplier = doc.matched_party
        if doc.date:
            new_doc.set_posting_time = 1
            new_doc.posting_date = doc.date
            new_doc.bill_date = doc.date
            new_doc.due_date = doc.date
        if doc.invoice_number:
            new_doc.bill_no = doc.invoice_number
    else:
        if doc.party_type == "Customer" and doc.matched_party:
            new_doc.customer = doc.matched_party
        if doc.date:
            new_doc.set_posting_time = 1
            new_doc.posting_date = doc.date
            new_doc.due_date = doc.date
            
    company = new_doc.company or frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
    default_income_account = frappe.get_cached_value('Company', company, 'default_income_account') if company else None
    if not default_income_account:
        default_income_account = frappe.db.get_value("Account", {"company": company, "account_type": "Income Account", "is_group": 0}, "name")
        
    default_expense_account = frappe.get_cached_value('Company', company, 'default_expense_account') if company else None
    if not default_expense_account:
        default_expense_account = frappe.db.get_value("Account", {"company": company, "account_type": "Expense Account", "is_group": 0}, "name")

    for item in doc.extracted_items:
        new_item = new_doc.append("items", {})
        
        # aggressively set name
        extracted_name = item.extracted_item_name or item.description or item.item_name or "Unknown Item"
        
        if item.matched_item:
            new_item.item_code = item.matched_item
            item_data = frappe.db.get_value("Item", item.matched_item, ["item_name", "stock_uom"], as_dict=True)
            if item_data:
                new_item.item_name = item_data.item_name or extracted_name
                new_item.uom = item_data.stock_uom or "Nos"
            else:
                new_item.item_name = extracted_name
                new_item.uom = "Nos"
        else:
            new_item.item_name = extracted_name
            new_item.description = extracted_name
            new_item.uom = "Nos"
            
        new_item.qty = item.quantity or 1
        new_item.rate = item.rate or 0
        
        # Set default accounts to prevent mandatory field errors
        if target_doctype == "Sales Invoice" and default_income_account:
            new_item.income_account = default_income_account
        elif target_doctype == "Purchase Invoice" and default_expense_account:
            new_item.expense_account = default_expense_account
        
    new_doc.flags.ignore_mandatory = True
    new_doc.flags.ignore_validate = True
    new_doc.insert(ignore_permissions=True)
    
    if target_doctype == "Purchase Invoice":
        doc.db_set("purchase_invoice_ref", new_doc.name)
    else:
        doc.db_set("sales_invoice_ref", new_doc.name)
        
    doc.db_set("status", "Processed")
        
    return new_doc.name


@frappe.whitelist()
def get_generated_templates():
    import os, datetime
    settings = frappe.get_single("Invoice Parser Settings")
    templates_dir = settings.templates_directory or "/home/frappe/frappe-bench/sites/erp.sananahmad.dpdns.org/private/files/invoice_templates"
    if not templates_dir.startswith("/"):
        templates_dir = frappe.get_site_path(templates_dir)
    
    if not os.path.exists(templates_dir):
        return []
        
    templates = []
    for f in os.listdir(templates_dir):
        if f.endswith('.yml'):
            fpath = os.path.join(templates_dir, f)
            stat = os.stat(fpath)
            templates.append({
                "name": f,
                "size": stat.st_size,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
            
    templates.sort(key=lambda x: x['modified'], reverse=True)
    return templates


@frappe.whitelist()
def get_template_content(filename):
    import os
    settings = frappe.get_single("Invoice Parser Settings")
    templates_dir = settings.templates_directory or "/home/frappe/frappe-bench/sites/erp.sananahmad.dpdns.org/private/files/invoice_templates"
    if not templates_dir.startswith("/"):
        templates_dir = frappe.get_site_path(templates_dir)
    
    if not os.path.exists(templates_dir):
        return ""
        
    fpath = os.path.join(templates_dir, filename)
    if os.path.exists(fpath):
        with open(fpath, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

@frappe.whitelist()
def delete_template(filename):
    settings = frappe.get_doc("Invoice Parser Settings")
    templates_dir = settings.templates_directory or "/home/frappe/frappe-bench/sites/erp.sananahmad.dpdns.org/private/files/invoice_templates"
    if not templates_dir.startswith("/"):
        templates_dir = frappe.get_site_path(templates_dir)
        
    if not templates_dir or not os.path.isdir(templates_dir):
        frappe.throw("Invalid templates directory.")
        
    # Prevent directory traversal
    filename = os.path.basename(filename)
    file_path = os.path.join(templates_dir, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

@frappe.whitelist()
def save_template_content(filename, content):
    import os
    settings = frappe.get_single("Invoice Parser Settings")
    templates_dir = settings.templates_directory or "/home/frappe/frappe-bench/sites/erp.sananahmad.dpdns.org/private/files/invoice_templates"
    if not templates_dir.startswith("/"):
        templates_dir = frappe.get_site_path(templates_dir)
    
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir, exist_ok=True)
        
    fpath = os.path.join(templates_dir, filename)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def sync_template_file(doc, method):
    settings = frappe.get_single('Invoice Parser Settings')
    templates_dir = settings.templates_directory or '/home/frappe/frappe-bench/sites/erp.sananahmad.dpdns.org/private/files/invoice_templates'
    if not templates_dir.startswith('/'):
        templates_dir = frappe.get_site_path(templates_dir)
        
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir, exist_ok=True)
        
    fpath = os.path.join(templates_dir, f"{doc.template_name}.yml")
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(doc.content or '')

def delete_template_file(doc, method):
    settings = frappe.get_single('Invoice Parser Settings')
    templates_dir = settings.templates_directory or '/home/frappe/frappe-bench/sites/erp.sananahmad.dpdns.org/private/files/invoice_templates'
    if not templates_dir.startswith('/'):
        templates_dir = frappe.get_site_path(templates_dir)
        
    fpath = os.path.join(templates_dir, f"{doc.template_name}.yml")
    if os.path.exists(fpath):
        os.remove(fpath)

@frappe.whitelist()
def download_doctr_model():
    frappe.enqueue("invoice_parser.utils.invoice_parser._download_doctr_background", queue="long", timeout=1500)
    return True

def _download_doctr_background():
    try:
        frappe.logger().info("Starting doctr model download...")
        from invoice_parser.utils.doctr import _get_model
        _get_model()
        frappe.logger().info("Successfully downloaded doctr model to cache!")
    except Exception as e:
        frappe.logger().error(f"Failed to download doctr model: {e}")
