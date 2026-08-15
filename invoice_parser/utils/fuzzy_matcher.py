import frappe
import difflib

def match_party(company_name, threshold=70):
    """Fuzzy matches a party against Suppliers and Customers in ERPNext."""
    if not company_name:
        return None, None
        
    suppliers = frappe.get_all("Supplier", fields=["name", "supplier_name"])
    customers = frappe.get_all("Customer", fields=["name", "customer_name"])
    
    name_map = {}
    # Build dictionary of all possible names -> (doctype, docname)
    for s in suppliers:
        name_map[s.name.lower()] = ("Supplier", s.name)
        if s.supplier_name:
            name_map[s.supplier_name.lower()] = ("Supplier", s.name)
            
    for c in customers:
        name_map[c.name.lower()] = ("Customer", c.name)
        if c.customer_name:
            name_map[c.customer_name.lower()] = ("Customer", c.name)
            
    search_term = company_name.lower()
    
    # Exact match first
    if search_term in name_map:
        res = name_map[search_term]
        return {"doctype": res[0], "name": res[1]}
        
    all_names = list(name_map.keys())
    if not all_names:
        return None, None
        
    matches = difflib.get_close_matches(search_term, all_names, n=1, cutoff=threshold/100)
    if matches:
        res = name_map[matches[0]]
        return {"doctype": res[0], "name": res[1]}
            
    return None, None

def match_item(item_name_or_code, threshold=60):
    if not item_name_or_code:
        return None
        
    items = frappe.get_all("Item", fields=["name", "item_name", "item_code"])
    
    name_map = {}
    for i in items:
        name_map[i.name.lower()] = i.name
        if i.item_name:
            name_map[i.item_name.lower()] = i.name
        if i.item_code:
            name_map[i.item_code.lower()] = i.name
            
    search_term = item_name_or_code.lower()
    
    if search_term in name_map:
        return name_map[search_term]
        
    all_names = list(name_map.keys())
    if not all_names:
        return None
        
    matches = difflib.get_close_matches(search_term, all_names, n=1, cutoff=threshold/100)
    if matches:
        return name_map[matches[0]]
        
    return None
