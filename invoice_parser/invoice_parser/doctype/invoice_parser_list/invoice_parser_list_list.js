frappe.listview_settings['Invoice Parser List'] = {
    add_fields: ["status", "invoice_file", "purchase_invoice_ref", "sales_invoice_ref", "extracted_company_name", "total_amount"],
    
    get_indicator: function (doc) {
        if (doc.status === "Pending Review") {
            return [__("Pending Review"), "orange", "status,=,Pending Review"];
        } else if (doc.status === "Processing") {
            return [__("Processing"), "blue", "status,=,Processing"];
        } else if (doc.status === "Processed") {
            return [__("Processed"), "green", "status,=,Processed"];
        } else if (doc.status === "Failed") {
            return [__("Failed"), "red", "status,=,Failed"];
        } else if (doc.status === "Draft") {
            return [__("Draft"), "red", "status,=,Draft"];
        }
    },
    
    formatters: {
        invoice_file: function (value, df, doc) {
            if (value) {
                return `<a href="${value}" target="_blank"><img src="${value}" style="max-width: 50px; max-height: 50px; border-radius: 4px; border: 1px solid #ddd;"></a>`;
            }
            return "";
        }
    },
    
    onload: function(listview) {
        if (!listview._polling) {
            listview._polling = setInterval(() => {
                let has_processing = listview.data.some(d => d.status === "Processing");
                if (has_processing) {
                    listview.refresh();
                }
            }, 5000);
        }
    }
};

frappe.realtime.on('invoice_parsed', function(data) {
    if (window.cur_list && cur_list.doctype === 'Invoice Parser List') {
        cur_list.refresh();
    }
});

frappe.realtime.on('invoice_parse_failed', function(data) {
    if (window.cur_list && cur_list.doctype === 'Invoice Parser List') {
        cur_list.refresh();
    }
});
