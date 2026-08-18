# Metadata extraction for DocTypes
import frappe

def get_doctype_metadata(doctype_name: str) -> dict:
	"""Fetch DocType fields, labels, fieldtypes, child tables, etc."""
	if not doctype_name or not frappe.db.exists("DocType", doctype_name):
		frappe.throw(f"DocType '{doctype_name}' does not exist.", frappe.ValidationError)

	meta = frappe.get_meta(doctype_name)
	
	exclude_types = ("Section Break", "Column Break", "Tab Break", "HTML", "Button", "Fold")
	
	fields = []
	child_tables = {}
	currency_fields = []
	
	# Parse parent fields
	for df in meta.fields:
		if df.fieldtype not in exclude_types:
			fields.append({
				"fieldname": df.fieldname,
				"label": df.label or df.fieldname,
				"fieldtype": df.fieldtype,
				"options": df.options
			})
			if df.fieldtype in ("Currency", "Float", "Int"):
				currency_fields.append(df.fieldname)
				
		if df.fieldtype == "Table" and df.options:
			child_table_name = df.options
			if frappe.db.exists("DocType", child_table_name):
				child_meta = frappe.get_meta(child_table_name)
				child_fields = []
				for cdf in child_meta.fields:
					if cdf.fieldtype not in exclude_types:
						child_fields.append({
							"fieldname": cdf.fieldname,
							"label": cdf.label or cdf.fieldname,
							"fieldtype": cdf.fieldtype,
							"options": cdf.options
						})
						if cdf.fieldtype in ("Currency", "Float", "Int"):
							currency_fields.append(cdf.fieldname)
				child_tables[df.fieldname] = child_fields

	title_field = getattr(meta, "title_field", None)
	
	# Check if naming_series is a field
	naming_series = None
	if meta.has_field("naming_series"):
		naming_series = meta.get_field("naming_series").options or ""

	return {
		"doctype": doctype_name,
		"fields": fields,
		"child_tables": child_tables,
		"currency_fields": list(set(currency_fields)),
		"title_field": title_field,
		"naming_series": naming_series
	}
