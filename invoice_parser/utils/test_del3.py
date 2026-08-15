import frappe

def run():
    frappe.init(site="erp.sananahmad.dpdns.org")
    frappe.connect()

    links = frappe.get_all("Workspace Shortcut", filters=[["link_to", "like", "%Invoice Parse%"]])
    if links:
        print("Found shortcuts!", links)
        for l in links:
            frappe.delete_doc("Workspace Shortcut", l.name, force=1)
        frappe.db.commit()
    else:
        print("No workspace shortcuts found.")
        
    links = frappe.get_all("Workspace Link", filters=[["link_to", "like", "%Invoice Parse%"]])
    if links:
        print("Found links!", links)
        for l in links:
            frappe.delete_doc("Workspace Link", l.name, force=1)
        frappe.db.commit()
    else:
        print("No workspace links found.")
