import frappe
from frappe.modules.export_file import export_to_files

def unhide_party_type():
    frappe.init(site="erp.sananahmad.dpdns.org")
    frappe.connect()
    
    doc = frappe.get_doc("DocType", "Invoice Parser List")
    changed = False
    
    for f in doc.fields:
        if f.fieldname == "party_type":
            if f.hidden:
                f.hidden = 0
                changed = True
                
    if changed:
        doc.save(ignore_permissions=True)
        export_to_files(record_list=[["DocType", "Invoice Parser List"]], record_module="Invoice Parser")
        frappe.db.commit()
        print("Unhid party_type field")
    else:
        print("party_type already unhidden")

unhide_party_type()
