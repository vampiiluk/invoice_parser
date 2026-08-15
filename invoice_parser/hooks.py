app_name = "invoice_parser"
app_title = "Invoice Parser"
app_publisher = "Author"
app_description = "Invoice Parser"
app_email = "email@example.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "invoice_parser",
# 		"logo": "/assets/invoice_parser/logo.png",
# 		"title": "Invoice Parser",
# 		"route": "/invoice_parser",
# 		"has_permission": "invoice_parser.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/invoice_parser/css/invoice_parser.css"
# app_include_js = "/assets/invoice_parser/js/invoice_parser.js"

# include js, css files in header of web template
# web_include_css = "/assets/invoice_parser/css/invoice_parser.css"
# web_include_js = "/assets/invoice_parser/js/invoice_parser.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "invoice_parser/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "invoice_parser/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "invoice_parser.utils.jinja_methods",
# 	"filters": "invoice_parser.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "invoice_parser.install.before_install"
after_install = "invoice_parser.install.after_install"
after_migrate = "invoice_parser.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "invoice_parser.uninstall.before_uninstall"
# after_uninstall = "invoice_parser.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "invoice_parser.utils.before_app_install"
# after_app_install = "invoice_parser.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "invoice_parser.utils.before_app_uninstall"
# after_app_uninstall = "invoice_parser.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "invoice_parser.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "invoice_parser.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Invoice Template": {
		"on_update": "invoice_parser.utils.invoice_parser.sync_template_file",
		"on_trash": "invoice_parser.utils.invoice_parser.delete_template_file"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"invoice_parser.tasks.all"
# 	],
# 	"daily": [
# 		"invoice_parser.tasks.daily"
# 	],
# 	"hourly": [
# 		"invoice_parser.tasks.hourly"
# 	],
# 	"weekly": [
# 		"invoice_parser.tasks.weekly"
# 	],
# 	"monthly": [
# 		"invoice_parser.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "invoice_parser.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "invoice_parser.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "invoice_parser.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "invoice_parser.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["invoice_parser.utils.before_request"]
# after_request = ["invoice_parser.utils.after_request"]

# Job Events
# ----------
# before_job = ["invoice_parser.utils.before_job"]
# after_job = ["invoice_parser.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"invoice_parser.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []



fixtures = [
    {"dt": "Client Script", "filters": [["module", "=", "Invoice Parser"]]}
]
