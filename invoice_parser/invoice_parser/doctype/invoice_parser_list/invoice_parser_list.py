# Copyright (c) 2026, Author and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InvoiceParserList(Document):
	def on_trash(self):
		files = frappe.get_all("File", filters={"attached_to_doctype": self.doctype, "attached_to_name": self.name})
		for f in files:
			frappe.delete_doc("File", f.name, ignore_permissions=True, force=True)
