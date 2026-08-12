// Copyright (c) 2026, Author and contributors
// For license information, please see license.txt

frappe.ui.form.on("Invoice Parser Settings", {
    refresh: function(frm) {
        frm.add_custom_button(__('Download OCR Model'), function() {
            frappe.call({
                method: "invoice_parser.utils.invoice_parser.download_doctr_model",
                callback: function(r) {
                    frappe.msgprint(__('Model download initiated in background. Check error logs for status.'));
                }
            });
        }).addClass('btn-primary');
    }
});
