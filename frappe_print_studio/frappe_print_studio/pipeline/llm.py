# LLM Provider abstraction and client implementations
import os
import requests
import json
import logging
import frappe

logger = logging.getLogger(__name__)

def resolve_file_path(file_url: str) -> str:
	"""Resolves a file URL or path to a local absolute file path."""
	if not file_url:
		return None
		
	# If already exists on system
	if os.path.exists(file_url):
		return file_url

	# Check File DocType
	if frappe.db.exists("File", file_url):
		from frappe.utils.file_manager import get_file_path
		return get_file_path(file_url)

	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if file_name:
		from frappe.utils.file_manager import get_file_path
		return get_file_path(file_name)

	# Try relative path resolution inside site folder
	site_path = frappe.get_site_path()
	clean_url = file_url.lstrip("/")
	
	path_pub = os.path.join(site_path, "public", clean_url)
	if os.path.exists(path_pub):
		return path_pub

	path_priv = os.path.join(site_path, clean_url)
	if os.path.exists(path_priv):
		return path_priv

	return None

class LLMProvider:
	def __init__(self, api_key: str = None, api_base: str = None, model_name: str = None):
		self.api_key = api_key
		self.api_base = api_base
		self.model_name = model_name

	def generate(self, prompt: str, system_instruction: str = None, attachments: list = None) -> str:
		raise NotImplementedError("Each provider must implement the generate method")

class GeminiProvider(LLMProvider):
	def generate(self, prompt: str, system_instruction: str = None, attachments: list = None) -> str:
		import time
		requested_model = self.model_name or "gemini-3.5-flash"
		models_to_try = [requested_model]
		for fallback in ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-flash-latest"]:
			if fallback not in models_to_try:
				models_to_try.append(fallback)

		last_error = None
		for model in models_to_try:
			url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
			headers = {"Content-Type": "application/json"}
			
			parts = [{"text": prompt}]
			
			if attachments:
				for att in attachments:
					file_path = resolve_file_path(att)
					if file_path and os.path.exists(file_path):
						import mimetypes
						import base64
						mime_type, _ = mimetypes.guess_type(file_path)
						if not mime_type:
							mime_type = "application/octet-stream"
						with open(file_path, "rb") as f:
							b64_data = base64.b64encode(f.read()).decode("utf-8")
						parts.append({
							"inlineData": {
								"mimeType": mime_type,
								"data": b64_data
							}
						})

			payload = {
				"contents": [
					{
						"parts": parts
					}
				]
			}
			if system_instruction:
				payload["systemInstruction"] = {
					"parts": [{"text": system_instruction}]
				}

			max_retries = 3
			for attempt in range(max_retries):
				try:
					logger.info(f"Calling Gemini API with model {model} (attempt {attempt + 1})")
					response = requests.post(url, headers=headers, json=payload, timeout=120)
					
					# Retry on 429 (rate limit) or 503 (service unavailable)
					if response.status_code in [429, 503]:
						logger.warning(f"Gemini API returned status {response.status_code} for {model}. Retrying...")
						if attempt < max_retries - 1:
							time.sleep(2 ** attempt)
							continue

					response.raise_for_status()
					res_data = response.json()
					
					candidates = res_data.get("candidates", [])
					if candidates:
						parts = candidates[0].get("content", {}).get("parts", [])
						if parts:
							return parts[0].get("text", "")
					return ""
				except Exception as e:
					last_error = e
					logger.warning(f"Failed Gemini attempt {attempt + 1} with model {model}: {e}")
					if attempt < max_retries - 1:
						time.sleep(2 ** attempt)
			
			logger.warning(f"All attempts failed for model {model}. Trying next fallback...")

		logger.error(f"Gemini API call failed for all models: {last_error}")
		raise RuntimeError(f"Gemini API Error: {last_error}")

class OpenAIProvider(LLMProvider):
	def generate(self, prompt: str, system_instruction: str = None, attachments: list = None) -> str:
		model = self.model_name or "gpt-4o-mini"
		url = self.api_base or "https://api.openai.com/v1/chat/completions"
		
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self.api_key}"
		}
		
		messages = []
		if system_instruction:
			messages.append({"role": "system", "content": system_instruction})
		
		if attachments:
			content_blocks = [{"type": "text", "text": prompt}]
			for att in attachments:
				file_path = resolve_file_path(att)
				if file_path and os.path.exists(file_path):
					import mimetypes
					import base64
					mime_type, _ = mimetypes.guess_type(file_path)
					if mime_type and mime_type.startswith("image/"):
						with open(file_path, "rb") as f:
							b64_data = base64.b64encode(f.read()).decode("utf-8")
						content_blocks.append({
							"type": "image_url",
							"image_url": {
								"url": f"data:{mime_type};base64,{b64_data}"
							}
						})
					else:
						logger.warning(f"OpenAI does not support non-image attachment: {att}")
			messages.append({"role": "user", "content": content_blocks})
		else:
			messages.append({"role": "user", "content": prompt})
		
		payload = {
			"model": model,
			"messages": messages,
			"temperature": 0.2
		}

		try:
			response = requests.post(url, headers=headers, json=payload, timeout=120)
			response.raise_for_status()
			res_data = response.json()
			return res_data["choices"][0]["message"]["content"]
		except Exception as e:
			logger.error(f"OpenAI API call failed: {e}")
			raise RuntimeError(f"OpenAI API Error: {e}")

class DeepSeekProvider(LLMProvider):
	def generate(self, prompt: str, system_instruction: str = None, attachments: list = None) -> str:
		model = self.model_name or "deepseek-chat"
		url = self.api_base or "https://api.deepseek.com/v1/chat/completions"
		
		headers = {
			"Content-Type": "application/json",
			"Authorization": f"Bearer {self.api_key}"
		}
		
		messages = []
		if system_instruction:
			messages.append({"role": "system", "content": system_instruction})
		messages.append({"role": "user", "content": prompt})
		
		payload = {
			"model": model,
			"messages": messages,
			"temperature": 0.2
		}

		try:
			response = requests.post(url, headers=headers, json=payload, timeout=120)
			response.raise_for_status()
			res_data = response.json()
			return res_data["choices"][0]["message"]["content"]
		except Exception as e:
			logger.error(f"DeepSeek API call failed: {e}")
			raise RuntimeError(f"DeepSeek API Error: {e}")

class MockProvider(LLMProvider):
	def generate(self, prompt: str, system_instruction: str = None, attachments: list = None) -> str:
		logger.warning("Using MockProvider to generate template.")
		# Return a standard visually-faithful mock HTML and CSS
		mock_html = """
<div class="invoice-box">
	<table cellpadding="0" cellspacing="0">
		<tr class="top">
			<td colspan="4">
				<table>
					<tr>
						<td class="title">
							<h2>INVOICE</h2>
						</td>
						<td class="align-right">
							Invoice #: INV-2026-0001<br>
							Created: August 8, 2026<br>
						</td>
					</tr>
				</table>
			</td>
		</tr>
		<tr class="information">
			<td colspan="4">
				<table>
					<tr>
						<td>
							<strong>Acme Corporation</strong><br>
							123 Enterprise Way, Tech City<br>
							GSTIN: 27AAAAA1111A1Z1
						</td>
						<td class="align-right">
							<strong>BILL TO:</strong><br>
							Global Industries Ltd<br>
							456 Corporate Towers, Mumbai
						</td>
					</tr>
				</table>
			</td>
		</tr>
		<tr class="heading">
			<td>Item Description</td>
			<td class="align-right">Qty</td>
			<td class="align-right">Rate</td>
			<td class="align-right">Amount</td>
		</tr>
		<tr class="item">
			<td>Premium Cloud Subscription</td>
			<td class="align-right">12</td>
			<td class="align-right">100.00</td>
			<td class="align-right">1,200.00</td>
		</tr>
		<tr class="item">
			<td>Implementation & Setup</td>
			<td class="align-right">1</td>
			<td class="align-right">500.00</td>
			<td class="align-right">500.00</td>
		</tr>
		<tr class="total">
			<td colspan="2"></td>
			<td class="align-right"><strong>Subtotal:</strong></td>
			<td class="align-right">1,700.00</td>
		</tr>
		<tr class="total">
			<td colspan="2"></td>
			<td class="align-right"><strong>CGST (9%):</strong></td>
			<td class="align-right">153.00</td>
		</tr>
		<tr class="total">
			<td colspan="2"></td>
			<td class="align-right"><strong>SGST (9%):</strong></td>
			<td class="align-right">153.00</td>
		</tr>
		<tr class="total">
			<td colspan="2"></td>
			<td class="align-right"><strong>Total Amount:</strong></td>
			<td class="align-right"><strong>2,006.00</strong></td>
		</tr>
	</table>
	<div class="footer">
		<strong>Terms & Conditions:</strong><br>
		Payment due within 30 days.<br><br>
		Thank you for your business!
	</div>
</div>
"""
		mock_css = """
body {
	font-family: 'Helvetica Neue', 'Helvetica', Helvetica, Arial, sans-serif;
	color: #555;
	margin: 0;
	padding: 20px;
}
.invoice-box {
	max-width: 800px;
	margin: auto;
	padding: 30px;
	border: 1px solid #eee;
	box-shadow: 0 0 10px rgba(0, 0, 0, 0.15);
	font-size: 14px;
	line-height: 24px;
	color: #555;
	background: #fff;
}
.invoice-box table {
	width: 100%;
	line-height: inherit;
	text-align: left;
	border-collapse: collapse;
}
.invoice-box table td {
	padding: 8px;
	vertical-align: top;
}
.invoice-box table tr td.align-right {
	text-align: right;
}
.invoice-box table tr.top table td {
	padding-bottom: 20px;
}
.invoice-box table tr.top table td.title h2 {
	font-size: 28px;
	line-height: 28px;
	color: #333;
	margin: 0;
}
.invoice-box table tr.information table td {
	padding-bottom: 40px;
}
.invoice-box table tr.heading td {
	background: #f8f9fa;
	border-bottom: 1px solid #ddd;
	font-weight: bold;
}
.invoice-box table tr.item td {
	border-bottom: 1px solid #eee;
}
.invoice-box table tr.item.last td {
	border-bottom: none;
}
.invoice-box table tr.total td {
	padding-top: 4px;
	padding-bottom: 4px;
}
.invoice-box .footer {
	margin-top: 50px;
	border-top: 1px solid #eee;
	padding-top: 20px;
	font-size: 12px;
	color: #777;
}
"""
		# We return a JSON representation containing the keys
		return json.dumps({
			"html": mock_html,
			"css": mock_css
		})

def get_active_provider() -> LLMProvider:
	"""Fetch credentials from Print Studio Settings DocType or fallback to env variables."""
	if frappe.flags.in_test:
		return MockProvider()

	provider_type = "Mock"
	api_key = None
	api_base = None
	model_name = None

	try:
		# Check if settings doctype exists and is populated
		if frappe.db.exists("DocType", "Print Studio Settings"):
			settings = frappe.get_single("Print Studio Settings")
			if settings.llm_provider:
				provider_type = settings.llm_provider
				api_key = settings.get_password("api_key") if settings.api_key else None
				api_base = settings.api_base
				model_name = settings.model_name
	except Exception as e:
		logger.warning(f"Failed to fetch Print Studio Settings: {e}. Checking environment variables.")

	# Fallback to environment variables if database settings aren't set
	if provider_type == "Mock" or not api_key:
		if os.environ.get("GEMINI_API_KEY"):
			provider_type = "Gemini"
			api_key = os.environ.get("GEMINI_API_KEY")
			model_name = os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash"
		elif os.environ.get("OPENAI_API_KEY"):
			provider_type = "OpenAI"
			api_key = os.environ.get("OPENAI_API_KEY")
			model_name = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
		elif os.environ.get("DEEPSEEK_API_KEY"):
			provider_type = "DeepSeek"
			api_key = os.environ.get("DEEPSEEK_API_KEY")
			model_name = os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"

	# Instantiate provider
	if provider_type == "Gemini" and api_key:
		return GeminiProvider(api_key, api_base, model_name)
	elif provider_type == "OpenAI" and api_key:
		return OpenAIProvider(api_key, api_base, model_name)
	elif provider_type == "DeepSeek" and api_key:
		return DeepSeekProvider(api_key, api_base, model_name)
	else:
		return MockProvider()
