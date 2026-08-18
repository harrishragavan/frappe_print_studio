# Layout region classification heuristics
from typing import List, Tuple
from frappe_print_studio.frappe_print_studio.pipeline.schema import OCRBlock, OCRResult, LayoutRegion

def detect_regions(ocr_result: OCRResult, metadata: dict) -> List[LayoutRegion]:
	"""
	Groups OCR blocks into semantic layout regions (Header, Table, Totals, Footer)
	using spatial proximity and keyword analysis.
	"""
	width = metadata.get("width", 612.0)
	height = metadata.get("height", 792.0)

	blocks = ocr_result.blocks
	if not blocks:
		return []

	# 1. Sort blocks top-to-bottom, then left-to-right
	sorted_blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

	# 2. Group blocks into horizontal lines (blocks sharing similar y coordinates)
	lines: List[List[OCRBlock]] = []
	for block in sorted_blocks:
		placed = False
		# Try to add to an existing line if it overlaps vertically
		for line in lines:
			# Calculate vertical overlap
			line_ymin = min(b.bbox[1] for b in line)
			line_ymax = max(b.bbox[3] for b in line)
			line_height = line_ymax - line_ymin

			# Overlap threshold (e.g. 50% vertical overlap)
			overlap_min = max(line_ymin, block.bbox[1])
			overlap_max = min(line_ymax, block.bbox[3])
			overlap = overlap_max - overlap_min

			block_height = block.bbox[3] - block.bbox[1]
			min_h = min(line_height, block_height)

			if min_h > 0 and overlap / min_h > 0.4:
				line.append(block)
				placed = True
				break

		if not placed:
			lines.append([block])

	# Sort blocks within each line left-to-right
	for line in lines:
		line.sort(key=lambda b: b.bbox[0])

	# Sort lines top-to-bottom
	lines.sort(key=lambda l: min(b.bbox[1] for b in l))

	# 3. Group lines into larger vertical clusters (sections) based on vertical gaps
	sections: List[List[List[OCRBlock]]] = []
	current_section = []
	
	for i, line in enumerate(lines):
		if not current_section:
			current_section.append(line)
			continue

		prev_line = lines[i - 1]
		prev_line_ymax = max(b.bbox[3] for b in prev_line)
		curr_line_ymin = min(b.bbox[1] for b in line)
		gap = curr_line_ymin - prev_line_ymax

		# Average height of lines as scaling factor
		prev_line_h = prev_line_ymax - min(b.bbox[1] for b in prev_line)
		curr_line_h = max(b.bbox[3] for b in line) - curr_line_ymin
		avg_h = (prev_line_h + curr_line_h) / 2.0

		# If gap is larger than 2.0 lines, we start a new section
		if gap > avg_h * 2.5:
			sections.append(current_section)
			current_section = [line]
		else:
			current_section.append(line)

	if current_section:
		sections.append(current_section)

	# 4. Classify sections into LayoutRegions
	regions: List[LayoutRegion] = []
	
	for idx, section in enumerate(sections):
		# Flatten section to list of blocks
		sec_blocks = [b for line in section for b in line]
		
		# Compute section bounding box
		sec_xmin = min(b.bbox[0] for b in sec_blocks)
		sec_ymin = min(b.bbox[1] for b in sec_blocks)
		sec_xmax = max(b.bbox[2] for b in sec_blocks)
		sec_ymax = max(b.bbox[3] for b in sec_blocks)
		sec_bbox = (sec_xmin, sec_ymin, sec_xmax, sec_ymax)
		
		# Calculate center y of section
		center_y = (sec_ymin + sec_ymax) / 2.0
		center_y_ratio = center_y / height
		center_x = (sec_xmin + sec_xmax) / 2.0
		center_x_ratio = center_x / width
		
		# Section text content for keyword matching
		sec_text_lower = " ".join([b.text for b in sec_blocks]).lower()
		
		# Define table headers keywords
		table_keywords = ["item", "description", "qty", "quantity", "rate", "price", "amount", "total", "subtotal"]
		has_table_hdr = any(kw in sec_text_lower for kw in ["qty", "quantity", "rate", "price"]) and any(kw in sec_text_lower for kw in ["item", "description"])
		
		# Check layout properties to classify
		if center_y_ratio < 0.35:
			# Top part of document: Header or billing
			region_type = "header"
		elif center_y_ratio > 0.85:
			# Bottom part of document: Footer
			region_type = "footer"
		elif has_table_hdr or (0.30 <= center_y_ratio <= 0.78 and len(section) >= 3 and any(kw in sec_text_lower for kw in table_keywords)):
			# Contains table-like characteristics
			region_type = "table"
		elif center_y_ratio >= 0.55 and center_y_ratio <= 0.88 and center_x_ratio > 0.5:
			# Totals block is usually bottom right
			# Let's check for totals keywords
			if any(kw in sec_text_lower for kw in ["total", "subtotal", "gst", "cgst", "sgst", "tax", "vat"]):
				region_type = "totals"
			else:
				region_type = "text"
		else:
			region_type = "text"
			
		regions.append(LayoutRegion(
			id=f"region_{idx}_{region_type}",
			region_type=region_type,
			bbox=sec_bbox,
			contained_blocks=sec_blocks,
			confidence=0.95
		))

	# Ensure we have at least one of each expected region types if possible
	# Merge adjacent regions of the same type if necessary
	return regions
