// Copyright (c) 2026, Author and contributors
// For license information, please see license.txt

frappe.ui.form.on("Invoice Parser List", {
    refresh: function(frm) {
        frm.events.update_total_count(frm);
        
        // Add sleek top-bar buttons instead
        if (frm.doc.docstatus === 0 && !frm.is_new()) {
            frm.add_custom_button(__('Process Invoice'), function() {
                frm.events.process_invoice_action(frm, 0);
            }).addClass('btn-primary');
            
            frm.add_custom_button(__('Process via AI'), function() {
                frm.events.process_invoice_action(frm, 1);
            }).addClass('btn-secondary');
            
            if (['Pending Review', 'Completed', 'Review Needed', 'Processed'].includes(frm.doc.status)) {
                let create_options = [
                    "Purchase Invoice", 
                    "Sales Invoice", 
                    "Purchase Order",
                    "Sales Order",
                    "Quotation",
                    "Supplier Quotation"
                ];
                
                create_options.forEach(dt => {
                    frm.add_custom_button(__(dt), function() {
                        create_invoice(frm, dt);
                    }, __('Create'));
                });
            }
            
            if (frm.doc.extracted_items && frm.doc.extracted_items.length) {
                let has_unmatched = frm.doc.extracted_items.some(r => !r.matched_item);
                if (has_unmatched) {
                    frm.add_custom_button(__('Add Unmatched Items to Item Master'), function() {
                        frm.events.add_items_to_master(frm, {add_all: true});
                    }).addClass('btn-primary');
                }
                frm.add_custom_button(__('Add Selected to Item Master'), function() {
                    let selected = frm.fields_dict.extracted_items.grid.get_selected_children();
                    if (!selected.length) {
                        frappe.msgprint(__('Tick rows in the Extracted Items table first.'));
                        return;
                    }
                    frm.events.add_items_to_master(frm, {row_names: selected.map(r => r.name)});
                });
            }
        }
        
        // Polling fallback if WebSockets are broken
        if (frm.doc.status === "Processing") {
            if (!frm._polling) {
                frm._polling = setInterval(() => {
                    frappe.db.get_value("Invoice Parser List", frm.doc.name, "status").then((r) => {
                        if (r && r.message && r.message.status !== "Processing") {
                            clearInterval(frm._polling);
                            frm._polling = null;
                            frappe.show_alert({message: __('Processing Completed'), indicator: 'green'});
                            frm.reload_doc();
                        }
                    });
                }, 3000);
            }
        } else {
            if (frm._polling) {
                clearInterval(frm._polling);
                frm._polling = null;
            }
        }
        
        // Document Viewer
        if (frm.doc.invoice_file) {
            let file_url = frm.doc.invoice_file;
            let html = "";
            let overlay_html = "";
            
            // Build Overlays if we have OCR geometry and extracted data
            if (frm.doc.ocr_geometry_data && frm.doc.raw_extracted_data) {
                try {
                    let geom = JSON.parse(frm.doc.ocr_geometry_data);
                    let ext_data = JSON.parse(frm.doc.raw_extracted_data);
                    
                    let values_to_find = [];
                    
                    // Helper to add permutations
                    let add_val = (v) => {
                        if (!v) return;
                        let s = String(v).trim();
                        values_to_find.push(s.toLowerCase());
                        
                        // If it's a date like 2020-11-25 00:00:00
                        if (s.includes('00:00:00')) {
                            let parts = s.split(' ')[0].split('-'); // [2020, 11, 25]
                            if (parts.length === 3) {
                                values_to_find.push(`${parts[1]}/${parts[2]}/${parts[0]}`);
                                values_to_find.push(`${parts[2]}/${parts[1]}/${parts[0]}`);
                                values_to_find.push(`${parts[2]}-${parts[1]}-${parts[0]}`);
                            }
                        }
                        
                        // If it's a number like 645.2, add 645.20
                        if (!isNaN(v) && s.includes('.')) {
                            let f = parseFloat(v);
                            values_to_find.push(f.toFixed(2));
                        }
                    };

                    // Extract flat values
                    for (let k in ext_data) {
                        if (ext_data[k] && typeof ext_data[k] !== 'object') {
                            add_val(ext_data[k]);
                        }
                    }
                    
                    // Extract line items
                    if (ext_data.lines && Array.isArray(ext_data.lines)) {
                        ext_data.lines.forEach(row => {
                            for (let k in row) {
                                if (row[k] && typeof row[k] !== 'object') {
                                    add_val(row[k]);
                                }
                            }
                        });
                    }
                    
                    // Filter out tiny common words
                    values_to_find = values_to_find.filter(v => v.length > 2);
                    
                    if (geom.pages && geom.pages.length > 0) {
                        let page = geom.pages[0]; // Assume first page
                        page.blocks.forEach(b => {
                            b.lines.forEach(l => {
                                l.words.forEach(w => {
                                    if (!w.value) return;
                                    let word_val = w.value.toLowerCase().replace(/[$€£,]/g, ''); // strip currency/commas
                                    
                                    // Check if the word exactly matches or contains/is-contained-by our target values
                                    let is_match = values_to_find.some(val => {
                                        let v = val.toLowerCase();
                                        return v === word_val || (v.length > 3 && (v.includes(word_val) || word_val.includes(v)));
                                    });
                                    
                                    if (is_match) {
                                        let top_left = w.geometry[0];
                                        let bottom_right = w.geometry[1];
                                        let left = top_left[0] * 100;
                                        let top = top_left[1] * 100;
                                        let width = (bottom_right[0] - top_left[0]) * 100;
                                        let height = (bottom_right[1] - top_left[1]) * 100;
                                        
                                        overlay_html += `<div style="position:absolute; left:${left}%; top:${top}%; width:${width}%; height:${height}%; border: 2px solid #ff5858; background-color: rgba(255, 88, 88, 0.3); z-index: 10; border-radius: 2px;" title="Extracted Value: ${w.value}"></div>`;
                                    }
                                });
                            });
                        });
                    }
                } catch(e) { console.error("Error drawing bounding boxes", e); }
            }

            if (file_url.toLowerCase().endsWith(".pdf")) {
                html = `<div style="position:relative; width:100%; aspect-ratio: 1 / 1.414; border: 1px solid #d1d8dd; overflow: hidden;">
                            ${overlay_html ? `<div style="position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:20;">${overlay_html}</div>` : ''}
                            <embed src="${file_url}" type="application/pdf" width="100%" height="100%" />
                        </div>
                        <p class="text-muted text-center mt-2"><small>Note: Overlays on PDFs may not align perfectly if the browser viewer zooms/scrolls independently. Works best with images.</small></p>`;
            } else {
                html = `<div style="position:relative; display:inline-block; width:100%; border: 1px solid #d1d8dd;">
                            ${overlay_html}
                            <img src="${file_url}" style="width:100%; display:block;" />
                        </div>`;
            }
            frm.get_field('document_viewer').$wrapper.html(html);
        } else {
            frm.get_field('document_viewer').$wrapper.html('<div class="text-muted text-center" style="padding: 50px;">Please attach an invoice file to view it here.</div>');
        }
    },

    invoice_file: function(frm) {
        frm.trigger('refresh');
    },

    process_invoice_action: function(frm, force_ai=0) {
        let run_job = () => {
            frappe.call({
                method: "invoice_parser.utils.invoice_parser.enqueue_invoice_processing",
                args: { docname: frm.doc.name, force_ai: force_ai },
                callback: function(r) {
                    frappe.show_alert({message: __('Invoice Processing Queued'), indicator:'green'});
                    frm.reload_doc();
                }
            });
        };
        
        if (frm.is_dirty()) {
            frm.save().then(() => run_job());
        } else {
            run_job();
        }
    },

    update_total_count: function(frm) {
        let rows = frm.doc.extracted_items || [];
        let total = 0;
        rows.forEach(r => {
            total += parseFloat(r.quantity) || 0;
        });
        frm.set_value("total_items", rows.length);
        frm.set_value("total_item_count", total);
    },

    add_items_to_master: function(frm, opts) {
        let d = new frappe.ui.Dialog({
            title: __('Add Items to Item Master'),
            fields: [
                {
                    fieldname: "update_existing_rates",
                    fieldtype: "Check",
                    label: __('Update default purchase rate for already-matched items'),
                    default: 0
                }
            ],
            primary_action_label: __('Add Items'),
            primary_action: function() {
                let args = {
                    docname: frm.doc.name,
                    add_all: opts.add_all ? 1 : 0,
                    update_existing_rates: d.get_value("update_existing_rates") ? 1 : 0
                };
                if (opts.row_names) {
                    args.row_names = opts.row_names;
                }
                d.hide();
                frappe.call({
                    method: "invoice_parser.utils.invoice_parser.create_item_from_extracted_item",
                    args: args,
                    freeze: true,
                    freeze_message: __('Creating items...'),
                    callback: function(r) {
                        if (r.message) {
                            let m = r.message;
                            let parts = [];
                            if (m.created && m.created.length) {
                                parts.push(__('Created {0} item(s)', [m.created.length]));
                            }
                            if (m.updated && m.updated.length) {
                                parts.push(__('Updated purchase rate for {0} matched item(s)', [m.updated.length]));
                            }
                            if (m.skipped && m.skipped.length) {
                                parts.push(__('Skipped {0} (duplicate or empty)', [m.skipped.length]));
                            }
                            if (!parts.length) {
                                parts.push(m.message || __('Nothing to add.'));
                            }
                            frappe.show_alert({message: parts.join('. '), indicator: 'green'});
                            frm.reload_doc();
                        }
                    }
                });
            }
        });
        d.show();
    },
    
    on_destroy: function(frm) {
        if (frm._polling) {
            clearInterval(frm._polling);
            frm._polling = null;
        }
    }
});

function create_invoice(frm, target_doctype) {
    frappe.call({
        method: "invoice_parser.utils.invoice_parser.create_invoice_from_request",
        args: {
            docname: frm.doc.name,
            target_doctype: target_doctype
        },
        callback: function(r) {
            if (r.message) {
                frappe.set_route("Form", target_doctype, r.message);
                frappe.show_alert({message: __("Draft Invoice Created!"), indicator: "green"});
            }
        }
    });
}

frappe.ui.form.on("Invoice Parse Item", {
    quantity: function(frm, cdt, cdn) {
        frm.events.update_total_count(frm);
    }
});

frappe.realtime.on('invoice_parsed', function(data) {
    if (cur_frm && cur_frm.doc.name === data.docname) {
        frappe.show_alert({message: __('Invoice Extracted Successfully'), indicator: 'green'});
        cur_frm.reload_doc();
    }
});

frappe.realtime.on('invoice_parse_failed', function(data) {
    if (cur_frm && cur_frm.doc.name === data.docname) {
        frappe.show_alert({message: __('Invoice Extraction Failed. Please check Error Log.'), indicator: 'red'});
        cur_frm.reload_doc();
    }
});
