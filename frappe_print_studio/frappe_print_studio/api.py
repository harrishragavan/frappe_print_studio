# API endpoints for Frappe Print Studio
import os
import re
import json
import logging
import frappe
from frappe.utils.file_manager import get_file_path
from frappe_print_studio.frappe_print_studio.pipeline.ocr import run_ocr, OCREngineUnavailableError
from frappe_print_studio.frappe_print_studio.pipeline.layout import detect_regions
from frappe_print_studio.frappe_print_studio.pipeline.tables import detect_tables
from frappe_print_studio.frappe_print_studio.pipeline.schema import IntermediateDocumentSchema
from frappe_print_studio.frappe_print_studio.pipeline.htmlgen import generate_layout, parse_llm_response
from frappe_print_studio.frappe_print_studio.pipeline.llm import get_active_provider
from frappe_print_studio.frappe_print_studio.pipeline.metadata import get_doctype_metadata
from frappe_print_studio.frappe_print_studio.pipeline.mapping import map_fields
from frappe_print_studio.frappe_print_studio.pipeline.jinjagen import inject_jinja

logger = logging.getLogger(__name__)

@frappe.whitelist()
def create_job(file_url: str, target_doctype: str = None) -> dict:
	"""
	Create a new Print Studio Job and process it.
	"""
	frappe.only_for(["System Manager", "Print Studio Manager"])

	file_path = resolve_file_path(file_url)
	if file_path and file_path.lower().endswith(".pdf"):
		import pdfplumber
		try:
			with pdfplumber.open(file_path) as pdf:
				if len(pdf.pages) > 1:
					frappe.throw("Multi-page PDFs are not supported. Please upload a single-page document.", frappe.ValidationError)
		except Exception as e:
			if not isinstance(e, frappe.ValidationError):
				logger.error(f"Failed to check PDF page count: {e}")

	# Create document
	job = frappe.get_doc({
		"doctype": "Print Studio Job",
		"document_file": file_url,
		"target_doctype": target_doctype,
		"status": "Pending"
	})
	job.insert()
	frappe.db.commit()

	# Enqueue processing in the background (Task 8)
	frappe.enqueue(
		"frappe_print_studio.frappe_print_studio.api.process_job_pipeline",
		queue="default",
		timeout=600,
		job_id=job.name,
		job_name_arg=job.name
	)

	return {
		"message": "Job queued for background processing.",
		"job_name": job.name,
		"status": job.status
	}

@frappe.whitelist()
def get_job(job_name: str) -> dict:
	"""Retrieve the status and results of a Print Studio Job."""
	frappe.only_for(["System Manager", "Print Studio Manager"])
	if not frappe.db.exists("Print Studio Job", job_name):
		frappe.throw(f"Job {job_name} not found", frappe.NotFoundError)
		
	job = frappe.get_doc("Print Studio Job", job_name)
	
	# Parse JSON field if present
	schema_dict = {}
	if job.intermediate_schema:
		try:
			schema_dict = json.loads(job.intermediate_schema)
		except Exception:
			pass

	return {
		"name": job.name,
		"status": job.status,
		"error_message": job.error_message,
		"intermediate_schema": schema_dict,
		"generated_html": job.generated_html,
		"generated_css": job.generated_css,
		"generated_jinja": job.generated_jinja,
		"field_mappings": [
			{
				"detected_label": m.detected_label,
				"mapped_fieldname": m.mapped_fieldname,
				"confidence": m.confidence,
				"mapping_method": m.mapping_method,
				"is_override": m.is_override
			} for m in job.field_mappings
		]
	}

@frappe.whitelist()
def get_llm_settings() -> dict:
	"""Get current LLM settings (without API keys for safety)."""
	frappe.only_for(["System Manager", "Print Studio Manager"])
	settings = frappe.get_single("Print Studio Settings")
	return {
		"llm_provider": settings.llm_provider or "Mock",
		"api_base": settings.api_base or "",
		"model_name": settings.model_name or "",
		"has_api_key": bool(settings.api_key)
	}

@frappe.whitelist()
def save_llm_settings(llm_provider: str, api_key: str = None, api_base: str = None, model_name: str = None) -> dict:
	"""Save LLM settings."""
	frappe.only_for(["System Manager", "Print Studio Manager"])
	settings = frappe.get_single("Print Studio Settings")
	settings.llm_provider = llm_provider
	if api_key:
		settings.api_key = api_key
	settings.api_base = api_base
	settings.model_name = model_name
	settings.save()
	frappe.db.commit()
	return {"message": "Settings saved successfully"}

def process_job_pipeline(job_name: str = None, job_name_arg: str = None):
	"""
	Executes the document analysis and layout generation pipeline.
	This is run as a background task.
	"""
	job_name = job_name or job_name_arg
	if not job_name:
		raise ValueError("job_name or job_name_arg is required")

	try:
		# 1. Update job status to Processing
		job = frappe.get_doc("Print Studio Job", job_name)
		job.flags.ignore_links = True
		job.status = "Processing"
		job.save()
		frappe.db.commit()

		file_url = job.document_file
		file_path = resolve_file_path(file_url)

		if not file_path:
			raise FileNotFoundError(f"Could not resolve path for file URL: {file_url}")

		# 2. Run OCR
		logger.info(f"Running OCR for job {job_name} on {file_path}")
		ocr_result, metadata = run_ocr(file_path)

		# 3. Run Layout Detection
		logger.info(f"Running layout detection for job {job_name}")
		regions = detect_regions(ocr_result, metadata)

		# 4. Run Table Extraction
		logger.info(f"Running table extraction for job {job_name}")
		tables = detect_tables(regions)

		# 5. Build Intermediate Schema
		schema = IntermediateDocumentSchema(
			regions=regions,
			tables=tables,
			raw_ocr=ocr_result,
			metadata=metadata
		)
		job.intermediate_schema = schema.model_dump_json(indent=2)
		job.save()
		frappe.db.commit()

		# 6. Run LLM HTML/CSS Generation with attachment visual context (Task 6)
		logger.info(f"Running AI layout generation for job {job_name}")
		html_content, css_content = generate_layout(schema, file_path)

		job.generated_html = html_content
		job.generated_css = css_content
		
		# 7. Fetch target DocType metadata (Task 1)
		if not job.target_doctype:
			raise ValueError("target_doctype is required to generate field-bound print format")
		doctype_metadata = get_doctype_metadata(job.target_doctype)

		# 8. Map OCR-detected labels to real fields (Task 2)
		schema_dict = schema.model_dump() if hasattr(schema, "model_dump") else schema.dict()
		field_mappings = map_fields(schema_dict, doctype_metadata)
		
		# Persist field_mappings into job.field_mappings child table rows
		job.set("field_mappings", [])
		for m in field_mappings:
			method_str = m["mapping_method"].capitalize() if m["mapping_method"] else "Unmapped"
			# Normalise option string to match Select options
			if method_str not in ("Exact", "Fuzzy", "Semantic", "Manual", "Synonym", "Unmapped"):
				method_str = "Fuzzy"
			job.append("field_mappings", {
				"detected_label": m["detected_label"],
				"mapped_fieldname": m["mapped_fieldname"],
				"confidence": (m["confidence"] or 0.0) * 100.0,
				"mapping_method": method_str,
				"is_override": 0
			})

		# 9. Inject Jinja bindings (Task 3)
		job.generated_jinja = inject_jinja(html_content, css_content, field_mappings)
		
		job.status = "Completed"
		job.save()
		frappe.db.commit()
		logger.info(f"Job {job_name} completed successfully")

	except OCREngineUnavailableError as e:
		logger.error(f"OCR engine unavailable for job {job_name}: {e}")
		try:
			job = frappe.get_doc("Print Studio Job", job_name)
			job.flags.ignore_links = True
			job.status = "Failed"
			job.error_message = "OCR engine not installed. Install paddleocr or configure an alternative OCR backend."
			job.save()
			frappe.db.commit()
		except Exception as save_err:
			logger.error(f"Failed to save failure status for job {job_name}: {save_err}")

	except Exception as e:
		logger.exception(f"Failed to process job {job_name}: {e}")
		# Load latest document instance to avoid caching conflicts
		try:
			job = frappe.get_doc("Print Studio Job", job_name)
			job.flags.ignore_links = True
			job.status = "Failed"
			job.error_message = str(e)
			job.save()
			frappe.db.commit()
		except Exception as save_err:
			logger.error(f"Failed to save failure status for job {job_name}: {save_err}")

def resolve_file_path(file_url: str) -> str:
	"""Resolves a file URL or path to a local absolute file path."""
	if not file_url:
		return None
		
	# If already exists on system
	if os.path.exists(file_url):
		return file_url

	# Check File DocType
	# If the user passes a file name (e.g. "a1b2c3d4")
	if frappe.db.exists("File", file_url):
		return get_file_path(file_url)

	# If the user passes a file_url (e.g. "/files/invoice.pdf")
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if file_name:
		return get_file_path(file_name)

	# Try relative path resolution inside site folder
	site_path = frappe.get_site_path()
	clean_url = file_url.lstrip("/")
	
	# Look in site public files
	path_pub = os.path.join(site_path, "public", clean_url)
	if os.path.exists(path_pub):
		return path_pub

	# Look in site private files
	path_priv = os.path.join(site_path, clean_url)
	if os.path.exists(path_priv):
		return path_priv

	return None

@frappe.whitelist()
def deploy_print_format(job_name: str, html: str, css: str) -> dict:
	"""
	Creates or updates a standard Print Format in Frappe using the generated HTML/CSS.
	"""
	frappe.only_for(["System Manager", "Print Studio Manager"])
	if not frappe.db.exists("Print Studio Job", job_name):
		frappe.throw(f"Job {job_name} not found")
		
	job = frappe.get_doc("Print Studio Job", job_name)
	
	# Update the job with the latest edited HTML/CSS
	job.generated_html = html
	job.generated_css = css
	job.generated_jinja = html
	job.save()
	frappe.db.commit()
	
	if not job.target_doctype:
		frappe.throw("No target DocType defined for this job.")

	# Combine HTML and CSS (using generated_jinja)
	combined_html = f"<style>\n{css}\n</style>\n{job.generated_jinja or html}"
	
	# Use the linked print format name if exists, otherwise create a default one
	print_format_name = job.print_format or f"Print Studio - {job.target_doctype}"
	
	if frappe.db.exists("Print Format", print_format_name):
		pf = frappe.get_doc("Print Format", print_format_name)
		pf.html = combined_html
		pf.save()
	else:
		pf = frappe.get_doc({
			"doctype": "Print Format",
			"name": print_format_name,
			"doc_type": job.target_doctype,
			"custom_format": 1,
			"html": combined_html,
			"standard": "No"
		})
		pf.insert()
		
	# Update the job link if it wasn't set
	if not job.print_format:
		job.print_format = pf.name
		job.save()
		
	frappe.db.commit()
	
	return {
		"message": "Print Format deployed successfully!",
		"print_format": pf.name
	}

SYSTEM_PROMPT_REFINE = """
You are a senior frontend developer specializing in building print format templates for the Frappe Framework and ERPNext.
Your task is to refine and edit an existing HTML layout and CSS stylesheet based on specific instructions provided by the user.

CRITICAL STYLING & COMPATIBILITY RULES for wkhtmltopdf:
1. DO NOT use CSS Flexbox (display: flex) or Grid (display: grid). wkhtmltopdf has poor and unpredictable support for them.
2. USE traditional HTML table layouts (`<table>`, `<tr>`, `<td>`) to align columns, side-by-side blocks, and headers.
3. Use absolute/relative print units (px, pt, mm, in) for margins, widths, and paddings.
4. Ensure explicit column widths (e.g. `<td style="width: 30%">`) are set on table headers or cells to maintain clean column alignments.
5. Apply page-break properties (`page-break-inside: avoid;`) to prevent tables or totals blocks from splitting awkwardly across pages.
6. Use standard, high-quality typography (like Arial, Helvetica, or sans-serif).
7. IMPORTANT: Use single quotes for all HTML attributes (e.g., class='invoice-box' or style='width: 30%') instead of double quotes, to ensure the JSON can be parsed cleanly without escape conflicts.

OUTPUT FORMAT:
You MUST respond with a raw JSON object containing exactly two keys: "html" and "css". Do not return any other text or explanation.

Example JSON output structure:
{
  "html": "<!-- Refined HTML layout -->\\n<div class='invoice-box'>...</div>",
  "css": "/* Refined CSS styling */\\n.invoice-box { width: 100%; }"
}
"""

@frappe.whitelist()
def refine_layout(job_name: str, html: str, css: str, prompt: str, attachments: list = None) -> dict:
	"""
	Refine the existing print format HTML and CSS based on user instructions.
	"""
	frappe.only_for(["System Manager", "Print Studio Manager"])
	if not frappe.db.exists("Print Studio Job", job_name):
		frappe.throw(f"Job {job_name} not found")
		
	if isinstance(attachments, str):
		try:
			attachments = json.loads(attachments)
		except Exception:
			attachments = [attachments]

	# Call active provider
	provider = get_active_provider()
	logger.info(f"Refining layout for job {job_name} using: {provider.__class__.__name__}")
	
	refinement_prompt = f"""
Here is the existing HTML and CSS code for the print format:

--- EXISTING HTML ---
{html}

--- EXISTING CSS ---
{css}

--- USER REQUEST ---
Please update the HTML and CSS according to this request:
"{prompt}"

Make sure the output is a valid JSON object matching the requested structure.
"""

	response = provider.generate(refinement_prompt, system_instruction=SYSTEM_PROMPT_REFINE, attachments=attachments)
	
	# If we got a mock result, we can just return it or parse it
	if provider.__class__.__name__ == "MockProvider":
		try:
			data = json.loads(response)
			html_content, css_content = data.get("html", ""), data.get("css", "")
		except Exception:
			html_content, css_content = html, css
	else:
		html_content, css_content = parse_llm_response(response)

	# Save updated version to Print Studio Job
	job = frappe.get_doc("Print Studio Job", job_name)
	
	# Run mapping & Jinja generation on the refined HTML (Task 3)
	if job.target_doctype:
		try:
			doctype_metadata = get_doctype_metadata(job.target_doctype)
			schema_dict = json.loads(job.intermediate_schema) if job.intermediate_schema else {}
			field_mappings = map_fields(schema_dict, doctype_metadata)
			html_content_jinja = inject_jinja(html_content, css_content, field_mappings)
		except Exception as err:
			logger.error(f"Failed to re-inject Jinja after refinement: {err}")
			html_content_jinja = html_content
	else:
		html_content_jinja = html_content

	job.generated_html = html_content
	job.generated_css = css_content
	job.generated_jinja = html_content_jinja
	
	if frappe.flags.in_test:
		job.flags.ignore_links = True
	job.save()
	frappe.db.commit()

	return {
		"html": html_content,
		"css": css_content,
		"jinja": html_content_jinja
	}

def parse_print_format_html(combined_html: str):
	"""Extract CSS from <style> blocks and return (html, css)."""
	if not combined_html:
		return "", ""
	
	style_match = re.search(r"<style>(.*?)</style>", combined_html, re.DOTALL | re.IGNORECASE)
	if style_match:
		css = style_match.group(1).strip()
		html = re.sub(r"<style>.*?</style>", "", combined_html, flags=re.DOTALL | re.IGNORECASE).strip()
	else:
		css = ""
		html = combined_html.strip()
		
	return html, css

@frappe.whitelist()
def get_custom_print_formats() -> list:
	"""Retrieve all Print Formats that have a valid doc_type."""
	frappe.only_for(["System Manager", "Print Studio Manager"])
	return frappe.get_all(
		"Print Format",
		filters={"doc_type": ["is", "set"]},
		fields=["name", "doc_type", "custom_format"]
	)

@frappe.whitelist()
def get_site_files() -> list:
	"""Get a list of uploaded files on the site."""
	frappe.only_for(["System Manager", "Print Studio Manager"])
	return frappe.get_all(
		"File",
		filters={"is_folder": 0},
		fields=["name", "file_name", "file_url", "file_size"],
		order_by="creation desc"
	)

@frappe.whitelist()
def create_job_from_print_format(print_format_name: str) -> dict:
	"""
	Create a Print Studio Job pre-loaded with HTML/CSS from an existing Print Format.
	"""
	frappe.only_for(["System Manager", "Print Studio Manager"])
	
	if not frappe.db.exists("Print Format", print_format_name):
		frappe.throw(f"Print Format {print_format_name} not found", frappe.NotFoundError)
		
	pf = frappe.get_doc("Print Format", print_format_name)
	
	# Parse HTML and CSS
	html, css = parse_print_format_html(pf.html)
	
	# Create a completed Print Studio Job
	job = frappe.get_doc({
		"doctype": "Print Studio Job",
		"target_doctype": pf.doc_type,
		"print_format": pf.name,
		"status": "Completed",
		"generated_html": html,
		"generated_css": css,
		"generated_jinja": html,
		"intermediate_schema": json.dumps({
			"regions": [],
			"tables": [],
			"metadata": {
				"width": 612.0,
				"height": 792.0
			}
		}, indent=2)
	})
	
	if frappe.flags.in_test:
		job.flags.ignore_links = True
	job.insert()
	frappe.db.commit()
	
	return {
		"job_name": job.name
	}
