# AI HTML/CSS generation from intermediate schema
import re
import json
import logging
from frappe_print_studio.frappe_print_studio.pipeline.schema import IntermediateDocumentSchema
from frappe_print_studio.frappe_print_studio.pipeline.llm import get_active_provider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a senior frontend developer specializing in building print format templates for the Frappe Framework and ERPNext.
Your task is to generate visually-faithful, production-ready HTML and CSS templates based on spatial document data (OCR regions, bounding boxes, text positions, and table structures) as well as the attached document image.

CRITICAL STYLING & COMPATIBILITY RULES for wkhtmltopdf:
1. DO NOT use CSS Flexbox (display: flex) or Grid (display: grid). wkhtmltopdf has poor and unpredictable support for them.
2. USE traditional HTML table layouts (`<table>`, `<tr>`, `<td>`) to align columns, side-by-side blocks, and headers.
3. Use absolute/relative print units (px, pt, mm, in) for margins, widths, and paddings.
4. Ensure explicit column widths (e.g. `<td style="width: 30%">`) are set on table headers or cells to maintain clean column alignments.
5. Apply page-break properties (`page-break-inside: avoid;`) to prevent tables or totals blocks from splitting awkwardly across pages.
6. Use standard, high-quality typography (like Arial, Helvetica, or sans-serif).
7. IMPORTANT: Use single quotes for all HTML attributes (e.g., class='invoice-box' or style='width: 30%') instead of double quotes, to ensure the JSON can be parsed cleanly without escape conflicts.
8. MATCH VISUAL STYLING: Make sure to extract colors, borders, shading, font weight, logo alignment, and spacing from the attached image to make the layout visually identical to the document image.
"""

def generate_layout(schema: IntermediateDocumentSchema, resolved_file_path: str = None) -> tuple[str, str]:
	"""
	Generate HTML and CSS representing the visual layout of the document
	based on the intermediate schema using the configured LLM provider.
	"""
	import os
	
	# 1. Format the schema into a readable representation for the LLM
	doc_w = schema.metadata.get("width", 612.0)
	doc_h = schema.metadata.get("height", 792.0)
	
	prompt_data = {
		"document_dimensions": {"width": doc_w, "height": doc_h},
		"layout_regions": [],
		"tables": []
	}
	
	for region in schema.regions:
		if region.region_type == "table":
			# Table structure is detailed separately
			continue
		
		# Collect text
		text_content = " ".join([b.text for b in region.contained_blocks])
		prompt_data["layout_regions"].append({
			"id": region.id,
			"type": region.region_type,
			"bbox": region.bbox,
			"text": text_content
		})
		
	for table in schema.tables:
		table_cells = []
		for cell in table.cells:
			table_cells.append({
				"row": cell.row_index,
				"col": cell.col_index,
				"row_span": cell.row_span,
				"col_span": cell.col_span,
				"text": cell.text,
				"bbox": cell.bbox
			})
		prompt_data["tables"].append({
			"id": table.id,
			"bbox": table.bbox,
			"rows_count": table.rows,
			"cols_count": table.columns,
			"cells": table_cells
		})
		
	prompt = f"""
Here is the spatial layout data of a business document (e.g. invoice/receipt).
Create an HTML layout and CSS stylesheet that matches this spatial layout visually:

Document Data:
{json.dumps(prompt_data, indent=2)}

Please render the layout faithfully:
- Place Header/Company info at the top.
- Align billing details appropriately.
- Represent tables with matching row and column contents.
- Align the totals block (subtotal, taxes, grand total) to the bottom-right as in the bbox coordinates.
- Ensure the result conforms to the wkhtmltopdf constraints (no flexbox/grid, table-based layouts for columns).
"""

	# 2. Call the active LLM provider with attachments
	attachments = []
	temp_png_path = None
	if resolved_file_path and os.path.exists(resolved_file_path):
		if resolved_file_path.lower().endswith(".pdf"):
			try:
				from frappe_print_studio.frappe_print_studio.pipeline.ocr import render_pdf_page_to_image
				img = render_pdf_page_to_image(resolved_file_path, 0)
				import tempfile
				temp_png_path = os.path.join(tempfile.gettempdir(), f"print_studio_tmp_{os.path.basename(resolved_file_path)}.png")
				img.save(temp_png_path, "PNG")
				attachments = [temp_png_path]
			except Exception as e:
				logger.error(f"Failed to render PDF page for LLM generation: {e}")
		else:
			attachments = [resolved_file_path]

	provider = get_active_provider()
	logger.info(f"Invoking LLM provider: {provider.__class__.__name__} with attachments: {attachments}")
	
	try:
		response = provider.generate(prompt, system_instruction=SYSTEM_PROMPT, attachments=attachments)
	finally:
		if temp_png_path and os.path.exists(temp_png_path):
			try:
				os.remove(temp_png_path)
			except Exception:
				pass
	
	# If we got a mock result, it's already a JSON dump
	if provider.__class__.__name__ == "MockProvider":
		try:
			data = json.loads(response)
			return data.get("html", ""), data.get("css", "")
		except Exception:
			pass
			
	# 3. Parse and extract HTML/CSS from LLM response
	return parse_llm_response(response)

def parse_llm_response(response: str) -> tuple[str, str]:
	"""Extract HTML and CSS from LLM response, supporting JSON or regex fallbacks."""
	import codecs

	# Strip markdown code blocks if the LLM wrapped the JSON in them
	cleaned = response.strip()
	if cleaned.startswith("```"):
		# Find the first newline and split
		lines = cleaned.splitlines()
		if lines[0].startswith("```"):
			lines = lines[1:]
		if lines and lines[-1].startswith("```"):
			lines = lines[:-1]
		cleaned = "\n".join(lines).strip()

	# Strip leading/trailing 'json' wrapper prefix if any
	if cleaned.lower().startswith("json"):
		cleaned = cleaned[4:].strip()

	# Try standard JSON parsing
	try:
		data = json.loads(cleaned)
		if isinstance(data, dict):
			return data.get("html", "").strip(), data.get("css", "").strip()
	except Exception as e:
		logger.warning(f"Failed to parse LLM response as JSON: {e}. Trying regex fallbacks...")

	# Fallback 1: Extract "html" and "css" fields using regex to handle unescaped quotes inside values
	html_content = ""
	css_content = ""

	# Try matching "html" key first then "css" key
	match_html_first = re.search(r'"html"\s*:\s*"(.*?)"\s*,\s*"css"\s*:\s*"(.*?)"', cleaned, re.DOTALL)
	# Try matching "css" key first then "html" key
	match_css_first = re.search(r'"css"\s*:\s*"(.*?)"\s*,\s*"html"\s*:\s*"(.*?)"', cleaned, re.DOTALL)

	if match_html_first:
		try:
			html_content = codecs.escape_decode(bytes(match_html_first.group(1), "utf-8"))[0].decode("utf-8")
			css_content = codecs.escape_decode(bytes(match_html_first.group(2), "utf-8"))[0].decode("utf-8")
		except Exception as err:
			logger.warning(f"Regex escape decode failed for html first: {err}")
			html_content = match_html_first.group(1).replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
			css_content = match_html_first.group(2).replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
	elif match_css_first:
		try:
			css_content = codecs.escape_decode(bytes(match_css_first.group(1), "utf-8"))[0].decode("utf-8")
			html_content = codecs.escape_decode(bytes(match_css_first.group(2), "utf-8"))[0].decode("utf-8")
		except Exception as err:
			logger.warning(f"Regex escape decode failed for css first: {err}")
			css_content = match_css_first.group(1).replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
			html_content = match_css_first.group(2).replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

	if html_content or css_content:
		return html_content.strip(), css_content.strip()

	# Fallback 2: Regex search for style and html blocks (for raw, non-JSON output)
	# Look for <style> tags
	style_match = re.search(r"<style[^>]*>(.*?)</style>", response, re.DOTALL | re.IGNORECASE)
	if style_match:
		css_content = style_match.group(1).strip()
		# Remove style block from response to get clean HTML
		html_content = re.sub(r"<style[^>]*>.*?</style>", "", response, flags=re.DOTALL | re.IGNORECASE).strip()
	else:
		html_content = response

	# Clean any remaining code fences from HTML/CSS
	html_content = re.sub(r"```(html|xml)?", "", html_content).strip()
	css_content = re.sub(r"```(css)?", "", css_content).strip()

	return html_content, css_content
