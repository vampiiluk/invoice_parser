# Copyright (c) 2026, invoice_parser contributors
# For license information, please see license.txt

import frappe


def after_install():
	from frappe.desk.doctype.desktop_icon.desktop_icon import create_desktop_icons_from_workspace

	# create_workspace_sidebar_for_workspaces() used to live here and is gone
	# from frappe as of 16.51.0. Its work is now done by the v16_0 patches
	# convert_sidebars, convert_custom_sidebars, convert_personal_sidebars and
	# move_custom_sidebar_workspaces, so calling it is neither possible nor
	# wanted - importing it is what broke `bench migrate` on this bench.
	create_desktop_icons_from_workspace()
	frappe.db.commit()
