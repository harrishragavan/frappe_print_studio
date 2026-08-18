# Jinja Generation Engine
from bs4 import BeautifulSoup

def inject_jinja(html_skeleton: str, css_content: str, field_mappings: list) -> str:
	"""Inject Jinja tags deterministically into the generated HTML skeleton."""
	if not html_skeleton:
		return html_skeleton

	soup = BeautifulSoup(html_skeleton, "html.parser")

	# 1. Process Table / Child Table fields first
	table_mappings = [m for m in field_mappings if m.get("target", "").startswith("child_table:")]
	if table_mappings:
		from collections import defaultdict
		mappings_by_table = defaultdict(list)
		for m in table_mappings:
			table_name = m["target"].split(":", 1)[1]
			mappings_by_table[table_name].append(m)
			
		for table_name, mappings in mappings_by_table.items():
			# Find the HTML table
			detected_headers = [m["detected_label"].lower() for m in mappings]
			
			target_table = None
			header_row = None
			header_indices = {} # cell_index -> mapping
			
			for table in soup.find_all("table"):
				for tr in table.find_all("tr"):
					cells = tr.find_all(["td", "th"])
					# Count how many cells match our detected headers
					matches = 0
					temp_indices = {}
					for idx, cell in enumerate(cells):
						cell_text = cell.get_text().strip().lower()
						for m in mappings:
							if m["detected_label"].lower() in cell_text or cell_text in m["detected_label"].lower():
								matches += 1
								temp_indices[idx] = m
								break
					# If a significant number of cells match, this is the header row
					if matches >= 2 or (len(cells) > 0 and matches == len(cells)):
						target_table = table
						header_row = tr
						header_indices = temp_indices
						break
				if target_table:
					break
					
			if target_table and header_row:
				all_rows = target_table.find_all("tr")
				header_row_idx = all_rows.index(header_row)
				
				# The data rows are the ones after the header row
				data_rows = all_rows[header_row_idx + 1:]
				if data_rows:
					# We take the first data row as the template row
					template_row = data_rows[0]
					
					# Replace template row cells
					cells = template_row.find_all("td")
					for idx, cell in enumerate(cells):
						mapping = header_indices.get(idx)
						if mapping:
							fieldname = mapping.get("mapped_fieldname")
							detected_label = mapping.get("detected_label", "")
							original_text = cell.get_text().strip()
							
							if fieldname:
								if mapping.get("is_currency"):
									cell.string = f"{{{{ row.{fieldname} | fmt_money }}}}"
								else:
									cell.string = f"{{{{ row.{fieldname} }}}}"
							else:
								cell.string = f"<!-- UNMAPPED: \"{detected_label}\" --> {original_text}"
								
					# Wrap the template row in Jinja loop
					template_row.insert_before(f"{{% for row in doc.{table_name} %}}")
					template_row.insert_after("{% endfor %}")
					
					# Remove other data rows
					for other_row in data_rows[1:]:
						other_row.decompose()

	# 2. Process Header/Non-table fields
	header_mappings = [m for m in field_mappings if m.get("target") == "header"]
	if header_mappings:
		# Walk all text nodes and replace matched header sample values
		# Sort mappings so that longer sample values are matched first
		sorted_mappings = sorted(
			header_mappings,
			key=lambda x: len(x.get("sample_value", "")),
			reverse=True
		)
		
		# Collect text nodes (ignoring script/style tag children)
		text_nodes = list(soup.find_all(text=True))
		for node in text_nodes:
			if node.parent and node.parent.name in ["script", "style"]:
				continue
				
			text = str(node)
			modified = False
			
			for m in sorted_mappings:
				sample_value = m.get("sample_value", "").strip()
				if not sample_value or len(sample_value) < 2:
					continue
					
				if sample_value in text:
					fieldname = m.get("mapped_fieldname")
					detected_label = m.get("detected_label", "")
					
					if fieldname:
						if m.get("is_currency"):
							rep = f"{{{{ doc.{fieldname} | fmt_money }}}}"
						else:
							rep = f"{{{{ doc.{fieldname} }}}}"
					else:
						rep = f"<!-- UNMAPPED: \"{detected_label}\" --> {sample_value}"
						
					text = text.replace(sample_value, rep)
					modified = True
					
			if modified:
				new_node = BeautifulSoup(text, "html.parser")
				node.replace_with(new_node)

	return str(soup)
