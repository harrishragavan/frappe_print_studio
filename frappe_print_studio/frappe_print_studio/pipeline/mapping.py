# Intelligent Field Mapper
import difflib

SYNONYMS = {
	"customer": ["bill to", "customer name", "client", "customer", "billed to", "invoice to"],
	"supplier": ["supplier", "vendor", "vendor name", "supplier name"],
	"posting_date": ["date", "invoice date", "billing date", "posting date", "issue date"],
	"grand_total": ["total", "grand total", "total amount", "amount due", "payable", "net total"],
	"subtotal": ["subtotal", "sub-total"],
	"gstin": ["gstin", "tax id", "vat no", "vat number", "tax number", "tax registration no"],
	"po_no": ["po number", "po #", "purchase order", "po no", "order number", "order no"],
	"due_date": ["due date", "payment due", "payment due date"],
	"name": ["invoice no", "invoice #", "invoice number", "bill no", "receipt no", "purchase order #", "po number"]
}

COLUMN_SYNONYMS = {
	"item_code": ["item", "item code", "code", "part no", "product id", "product code"],
	"item_name": ["description", "item description", "particulars", "item name", "name", "product"],
	"qty": ["qty", "quantity", "quantity ordered", "units", "count"],
	"rate": ["rate", "price", "unit price", "unit rate"],
	"amount": ["amount", "total", "line total", "net amount", "value"]
}

def get_label_value_pairs(regions):
	pairs = []
	for region in regions:
		if region.get("region_type") == "table":
			continue
		blocks = region.get("contained_blocks", [])
		i = 0
		while i < len(blocks):
			block = blocks[i]
			# Ensure we can read block as dict or object
			text = (block.get("text") if isinstance(block, dict) else getattr(block, "text", "")).strip()
			if not text:
				i += 1
				continue
			
			# Check if there is a colon
			if ":" in text:
				parts = text.split(":", 1)
				label_part = parts[0].strip()
				value_part = parts[1].strip()
				if value_part:
					pairs.append({
						"detected_label": label_part,
						"sample_value": value_part
					})
				else:
					if i + 1 < len(blocks):
						next_block = blocks[i+1]
						next_text = (next_block.get("text") if isinstance(next_block, dict) else getattr(next_block, "text", "")).strip()
						pairs.append({
							"detected_label": label_part,
							"sample_value": next_text
						})
						i += 1
			else:
				# Check for keywords
				lower_text = text.lower()
				known_keywords = ["bill to", "invoice no", "po number", "gstin", "date", "due date", "grand total", "subtotal", "customer", "supplier", "invoice #", "total"]
				is_known = any(kw in lower_text for kw in known_keywords)
				if is_known and i + 1 < len(blocks):
					next_block = blocks[i+1]
					next_text = (next_block.get("text") if isinstance(next_block, dict) else getattr(next_block, "text", "")).strip()
					pairs.append({
						"detected_label": text,
						"sample_value": next_text
					})
					i += 1
			i += 1
	return pairs

def fuzzy_match(label: str, target_fields: list, synonyms_dict: dict) -> tuple:
	"""Helper to fuzzy match a label against target fields."""
	label_lower = label.lower()
	best_field = None
	best_score = 0.0
	best_method = "unmapped"

	for field in target_fields:
		fieldname = field["fieldname"]
		field_label = field["label"]
		
		# 1. Exact match (case insensitive)
		if label_lower == fieldname.lower() or label_lower == field_label.lower():
			return field, 1.0, "exact"

		# 2. Synonym match
		if fieldname in synonyms_dict:
			for syn in synonyms_dict[fieldname]:
				if label_lower == syn or syn in label_lower or label_lower in syn:
					# Exact synonym match gets high score
					score = 0.95
					if score > best_score:
						best_score = score
						best_field = field
						best_method = "synonym"

		# 3. Fuzzy match
		score_label = difflib.SequenceMatcher(None, label_lower, field_label.lower()).ratio()
		score_name = difflib.SequenceMatcher(None, label_lower, fieldname.lower()).ratio()
		max_score = max(score_label, score_name)
		if max_score > best_score:
			best_score = max_score
			best_field = field
			best_method = "fuzzy"

	return best_field, best_score, best_method

def map_fields(intermediate_schema: dict, doctype_metadata: dict) -> list:
	"""Map OCR-detected labels to DocType fieldnames."""
	mappings = []

	# 1. Map Header/Non-table fields
	regions = intermediate_schema.get("regions", [])
	label_value_pairs = get_label_value_pairs(regions)

	parent_fields = doctype_metadata.get("fields", [])

	for pair in label_value_pairs:
		label = pair["detected_label"]
		sample_value = pair["sample_value"]
		
		best_field, best_score, best_method = fuzzy_match(label, parent_fields, SYNONYMS)

		if best_field and best_score >= 0.6:
			fieldname = best_field["fieldname"]
			is_currency = fieldname in doctype_metadata.get("currency_fields", [])
			mappings.append({
				"detected_label": label,
				"mapped_fieldname": fieldname,
				"target": "header",
				"confidence": best_score,
				"mapping_method": best_method,
				"sample_value": sample_value,
				"is_currency": is_currency
			})
		else:
			mappings.append({
				"detected_label": label,
				"mapped_fieldname": None,
				"target": "header",
				"confidence": best_score,
				"mapping_method": "unmapped",
				"sample_value": sample_value,
				"is_currency": False
			})

	# 2. Map Table columns
	tables = intermediate_schema.get("tables", [])
	child_tables = doctype_metadata.get("child_tables", {})

	if tables and child_tables:
		# Identify the correct child table (default to 'items' or first table)
		child_table_fieldname = "items" if "items" in child_tables else list(child_tables.keys())[0]
		child_table_fields = child_tables[child_table_fieldname]

		for table in tables:
			# Get table cells
			cells = table.get("cells", [])
			
			# Find header cells (row_index == 0)
			# Convert cell objects/dicts
			header_cells = []
			for c in cells:
				row = c.get("row_index") if isinstance(c, dict) else getattr(c, "row_index", None)
				col = c.get("col_index") if isinstance(c, dict) else getattr(c, "col_index", None)
				text = c.get("text") if isinstance(c, dict) else getattr(c, "text", "")
				if row == 0:
					header_cells.append((col, text))
			
			# Sort columns by index
			header_cells.sort()

			for col_idx, text in header_cells:
				text = text.strip()
				if not text:
					continue

				best_field, best_score, best_method = fuzzy_match(text, child_table_fields, COLUMN_SYNONYMS)

				if best_field and best_score >= 0.6:
					fieldname = best_field["fieldname"]
					is_currency = fieldname in doctype_metadata.get("currency_fields", [])
					mappings.append({
						"detected_label": text,
						"mapped_fieldname": fieldname,
						"target": f"child_table:{child_table_fieldname}",
						"confidence": best_score,
						"mapping_method": best_method,
						"sample_value": "",
						"is_currency": is_currency
					})
				else:
					mappings.append({
						"detected_label": text,
						"mapped_fieldname": None,
						"target": f"child_table:{child_table_fieldname}",
						"confidence": best_score,
						"mapping_method": "unmapped",
						"sample_value": "",
						"is_currency": False
					})

	return mappings
