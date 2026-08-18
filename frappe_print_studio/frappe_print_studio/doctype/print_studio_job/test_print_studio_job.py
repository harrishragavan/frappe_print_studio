# Copyright (c) 2026, harrish and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe_print_studio.frappe_print_studio.api import process_job_pipeline

class TestPrintStudioJob(FrappeTestCase):
	def test_pipeline_execution(self):
		# Get path to a real image file inside the app
		favicon_path = frappe.get_app_path("frappe_print_studio", "public", "frontend", "favicon.png")

		# Create a test job targeting Sales Invoice
		job = frappe.get_doc({
			"doctype": "Print Studio Job",
			"document_file": favicon_path,
			"target_doctype": "Sales Invoice",
			"status": "Pending"
		})
		job.flags.ignore_links = True
		job.insert()
		frappe.db.commit()

		# Run the pipeline synchronously to test all stages (OCR, Layout, Tables, LLM Gen)
		process_job_pipeline(job.name)

		# Reload the job from DB to get updated fields
		job.reload()

		# Check status and outputs
		self.assertEqual(job.status, "Completed")
		self.assertIsNotNone(job.intermediate_schema)
		self.assertIsNotNone(job.generated_html)
		self.assertIsNotNone(job.generated_css)

		# Verify that the mock OCR data contains header and footer blocks
		self.assertIn("invoice", job.intermediate_schema.lower())
		self.assertIn("<table", job.generated_html.lower())
		self.assertIn("font-family", job.generated_css.lower())

		# Cleanup
		job.delete()
		frappe.db.commit()

	def test_refine_layout_with_attachments(self):
		from frappe_print_studio.frappe_print_studio.api import refine_layout
		favicon_path = frappe.get_app_path("frappe_print_studio", "public", "frontend", "favicon.png")
		# create mock job
		job = frappe.get_doc({
			"doctype": "Print Studio Job",
			"document_file": favicon_path,
			"target_doctype": "Sales Invoice",
			"status": "Completed",
			"generated_html": "<div>Original</div>",
			"generated_css": ".original {}"
		})
		job.flags.ignore_links = True
		job.insert()
		frappe.db.commit()

		# test refine_layout using the Mock provider with attachments
		res = refine_layout(
			job_name=job.name,
			html="<div>Original</div>",
			css=".original {}",
			prompt="Change text to blue",
			attachments=["/files/mock_attachment.pdf"]
		)
		self.assertIsNotNone(res.get("html"))
		self.assertIsNotNone(res.get("css"))

		# clean up
		job.delete()
		frappe.db.commit()

	def test_create_job_multipage_pdf_validation(self):
		from unittest.mock import patch, MagicMock
		
		mock_pdf = MagicMock()
		mock_pdf.pages = [MagicMock(), MagicMock()] # 2 pages
		
		# Create dummy file path
		with patch("pdfplumber.open", return_value=mock_pdf):
			with patch("frappe_print_studio.frappe_print_studio.api.resolve_file_path", return_value="dummy.pdf"):
				# Should throw ValidationError
				self.assertRaises(
					frappe.ValidationError,
					frappe.get_attr("frappe_print_studio.frappe_print_studio.api.create_job"),
					file_url="/files/dummy_multipage.pdf",
					target_doctype="Sales Invoice"
				)

	def test_api_auth_checks(self):
		# Switch to a guest / non-manager user
		frappe.set_user("Guest")
		try:
			self.assertRaises(
				frappe.PermissionError,
				frappe.get_attr("frappe_print_studio.frappe_print_studio.api.create_job"),
				file_url="/files/dummy.pdf",
				target_doctype="Sales Invoice"
			)
		finally:
			frappe.set_user("Administrator")

	def test_doctype_metadata_fetching(self):
		from frappe_print_studio.frappe_print_studio.pipeline.metadata import get_doctype_metadata
		meta = get_doctype_metadata("Sales Invoice")
		self.assertIsNotNone(meta)
		self.assertIn("fields", meta)
		self.assertIn("child_tables", meta)
		# Check child tables includes items
		self.assertIn("items", meta["child_tables"])
		# Check that currency fields are extracted
		self.assertTrue(len(meta.get("currency_fields", [])) > 0)

	def test_field_mapping_and_jinja_generation(self):
		from frappe_print_studio.frappe_print_studio.pipeline.mapping import map_fields
		from frappe_print_studio.frappe_print_studio.pipeline.jinjagen import inject_jinja
		
		intermediate_schema = {
			"regions": [
				{
					"id": "reg1",
					"region_type": "header",
					"bbox": [10, 10, 100, 20],
					"contained_blocks": [
						{"text": "Customer Name: Acme Corp", "bbox": [10, 10, 200, 20]}
					]
				}
			],
			"tables": [
				{
					"id": "tab1",
					"bbox": [10, 30, 200, 100],
					"rows": 2,
					"columns": 2,
					"cells": [
						{"row_index": 0, "col_index": 0, "row_span": 1, "col_span": 1, "text": "Item Code", "bbox": [10, 30, 50, 40]},
						{"row_index": 0, "col_index": 1, "row_span": 1, "col_span": 1, "text": "Rate", "bbox": [51, 30, 100, 40]},
						{"row_index": 1, "col_index": 0, "row_span": 1, "col_span": 1, "text": "Item A", "bbox": [10, 41, 50, 50]},
						{"row_index": 1, "col_index": 1, "row_span": 1, "col_span": 1, "text": "$10.00", "bbox": [51, 41, 100, 50]}
					]
				}
			]
		}
		
		doctype_metadata = {
			"fields": [
				{"fieldname": "customer_name", "label": "Customer Name", "fieldtype": "Data"}
			],
			"child_tables": {
				"items": [
					{"fieldname": "item_code", "label": "Item Code", "fieldtype": "Link"},
					{"fieldname": "rate", "label": "Rate", "fieldtype": "Currency"}
				]
			},
			"currency_fields": ["rate"]
		}
		
		# Test mapping
		mappings = map_fields(intermediate_schema, doctype_metadata)
		self.assertTrue(len(mappings) > 0)
		
		# Check header mapping
		header_maps = [m for m in mappings if m["target"] == "header"]
		self.assertEqual(header_maps[0]["mapped_fieldname"], "customer_name")
		
		# Check table mapping
		table_maps = [m for m in mappings if m["target"] == "child_table:items"]
		self.assertTrue(any(t["mapped_fieldname"] == "item_code" for t in table_maps))
		self.assertTrue(any(t["mapped_fieldname"] == "rate" for t in table_maps))
		
		# Test Jinja injection
		html_skeleton = """
		<div>
			<div class="cust">Customer Name</div>
			<table>
				<tr>
					<th>Item Code</th>
					<th>Rate</th>
				</tr>
				<tr>
					<td>Item A</td>
					<td>$10.00</td>
				</tr>
			</table>
		</div>
		"""
		css = ".cust { color: red; }"
		
		jinja_html = inject_jinja(html_skeleton, css, mappings)
		
		# Should contain template loop and fields
		self.assertIn("{% for row in doc.items %}", jinja_html)
		self.assertIn("{{ row.item_code }}", jinja_html)
		self.assertIn("{{ row.rate | fmt_money }}", jinja_html)

	def test_edit_existing_print_format_flow(self):
		from frappe_print_studio.frappe_print_studio.api import (
			parse_print_format_html,
			get_custom_print_formats,
			get_site_files,
			create_job_from_print_format,
			deploy_print_format
		)
		
		# 1. Test parsing HTML and CSS
		pf_html_raw = "<style>\n.custom-style { color: blue; }\n</style>\n<div class='custom-style'>Hello</div>"
		html, css = parse_print_format_html(pf_html_raw)
		self.assertEqual(html, "<div class='custom-style'>Hello</div>")
		self.assertEqual(css, ".custom-style { color: blue; }")
		
		# Test parsing without style tag
		html_only, css_empty = parse_print_format_html("<div>Hello Only</div>")
		self.assertEqual(html_only, "<div>Hello Only</div>")
		self.assertEqual(css_empty, "")

		# 2. Test get custom print formats (should run without error)
		formats = get_custom_print_formats()
		self.assertIsInstance(formats, list)

		# 3. Test get site files (should run without error)
		files = get_site_files()
		self.assertIsInstance(files, list)

		# 4. Create dummy print format to test creation
		test_format_name = "Test Print Studio Format"
		if frappe.db.exists("Print Format", test_format_name):
			frappe.delete_doc("Print Format", test_format_name)
			
		pf_doc = frappe.get_doc({
			"doctype": "Print Format",
			"name": test_format_name,
			"doc_type": "Sales Invoice",
			"custom_format": 1,
			"html": pf_html_raw,
			"standard": "No"
		})
		pf_doc.insert()
		frappe.db.commit()

		try:
			# Test creating print studio job from existing print format
			result = create_job_from_print_format(test_format_name)
			job_name = result["job_name"]
			self.assertTrue(frappe.db.exists("Print Studio Job", job_name))
			
			job = frappe.get_doc("Print Studio Job", job_name)
			self.assertEqual(job.status, "Completed")
			self.assertEqual(job.target_doctype, "Sales Invoice")
			self.assertEqual(job.print_format, test_format_name)
			self.assertEqual(job.generated_html, "<div class='custom-style'>Hello</div>")
			self.assertEqual(job.generated_css, ".custom-style { color: blue; }")

			# 5. Test deploying back to the linked print format
			new_html = "<div class='custom-style'>Updated Hello</div>"
			new_css = ".custom-style { color: green; }"
			
			deploy_res = deploy_print_format(job_name, new_html, new_css)
			self.assertEqual(deploy_res["print_format"], test_format_name)
			
			# Reload print format from database to check updates
			pf_doc.reload()
			self.assertIn("color: green;", pf_doc.html)
			self.assertIn("Updated Hello", pf_doc.html)
			
			# Cleanup job
			job.delete()
		finally:
			# Cleanup print format
			pf_doc.delete()
			frappe.db.commit()

