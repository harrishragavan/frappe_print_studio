# Copyright (c) 2026, harrish and Contributors
# MIT License

import frappe
from frappe import _

no_cache = 1

def get_context():
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to access Print Studio"), frappe.PermissionError)

	# Check roles: require System Manager or Administrator
	roles = frappe.get_roles(frappe.session.user)
	if "System Manager" not in roles and "Administrator" not in roles:
		frappe.throw(_("You do not have permission to access Print Studio"), frappe.PermissionError)

	context = frappe._dict()
	context.boot = get_boot()
	return context

@frappe.whitelist(methods=["POST"])
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	return get_boot()

def get_boot():
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"site_name": frappe.local.site,
			"csrf_token": frappe.sessions.get_csrf_token(),
			"user": frappe.session.user,
		}
	)
