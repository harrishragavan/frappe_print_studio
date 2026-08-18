# Table recognition and structure extraction
from typing import List
from frappe_print_studio.frappe_print_studio.pipeline.schema import LayoutRegion, TableStructure, TableCell

def detect_tables(regions: List[LayoutRegion]) -> List[TableStructure]:
	"""
	Extract table grid structures (rows, columns, cell contents)
	from layout regions classified as 'table'.
	"""
	tables: List[TableStructure] = []

	for region in regions:
		if region.region_type != "table":
			continue

		blocks = region.contained_blocks
		if not blocks:
			continue

		# 1. Group blocks into rows based on vertical overlap
		sorted_blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
		rows: List[List] = []
		
		for block in sorted_blocks:
			placed = False
			for row in rows:
				row_ymin = min(b.bbox[1] for b in row)
				row_ymax = max(b.bbox[3] for b in row)
				row_height = row_ymax - row_ymin

				overlap_min = max(row_ymin, block.bbox[1])
				overlap_max = min(row_ymax, block.bbox[3])
				overlap = overlap_max - overlap_min

				block_height = block.bbox[3] - block.bbox[1]
				min_h = min(row_height, block_height)

				if min_h > 0 and overlap / min_h > 0.4:
					row.append(block)
					placed = True
					break
			if not placed:
				rows.append([block])

		# Sort blocks within each row left-to-right
		for row in rows:
			row.sort(key=lambda b: b.bbox[0])

		# Sort rows top-to-bottom
		rows.sort(key=lambda r: min(b.bbox[1] for b in r))

		if not rows:
			continue

		# 2. Determine column layout using the row with the most blocks
		# (usually the table header or a fully populated line item)
		template_row = max(rows, key=len)
		col_count = len(template_row)
		if col_count == 0:
			continue

		# Sort template row to get left-to-right column intervals
		template_row.sort(key=lambda b: b.bbox[0])
		
		# Define initial column intervals: list of (xmin, xmax)
		col_intervals = [(float(b.bbox[0]), float(b.bbox[2])) for b in template_row]

		# 3. Map each block in each row to a column index based on horizontal overlap
		cells: List[TableCell] = []
		
		for r_idx, row in enumerate(rows):
			for block in row:
				# Find the column interval with the highest horizontal overlap
				best_col_idx = 0
				best_overlap = -1.0
				
				b_xmin, b_xmax = block.bbox[0], block.bbox[2]
				b_width = b_xmax - b_xmin
				
				for c_idx, (c_xmin, c_xmax) in enumerate(col_intervals):
					# Calculate horizontal overlap
					overlap_xmin = max(b_xmin, c_xmin)
					overlap_xmax = min(b_xmax, c_xmax)
					overlap = max(0.0, overlap_xmax - overlap_xmin)
					
					if overlap > best_overlap:
						best_overlap = overlap
						best_col_idx = c_idx
						
				# If overlap is 0, assign to nearest column by distance to center
				if best_overlap <= 0:
					b_center = (b_xmin + b_xmax) / 2.0
					min_dist = float('inf')
					for c_idx, (c_xmin, c_xmax) in enumerate(col_intervals):
						c_center = (c_xmin + c_xmax) / 2.0
						dist = abs(b_center - c_center)
						if dist < min_dist:
							min_dist = dist
							best_col_idx = c_idx
				
				# Check if a cell already exists at this (row_idx, col_idx)
				# If so, append the text (merging multi-word cells)
				existing_cell = next((c for c in cells if c.row_index == r_idx and c.col_index == best_col_idx), None)
				if existing_cell:
					existing_cell.text += " " + block.text
					# Expand cell bbox to encompass both
					if existing_cell.bbox and block.bbox:
						ex_bbox = existing_cell.bbox
						new_bbox = (
							min(ex_bbox[0], block.bbox[0]),
							min(ex_bbox[1], block.bbox[1]),
							max(ex_bbox[2], block.bbox[2]),
							max(ex_bbox[3], block.bbox[3])
						)
						existing_cell.bbox = new_bbox
				else:
					cells.append(TableCell(
						row_index=r_idx,
						col_index=best_col_idx,
						row_span=1,
						col_span=1,
						text=block.text,
						bbox=block.bbox
					))

		# 4. Construct TableStructure
		table_id = f"table_{region.id}"
		tables.append(TableStructure(
			id=table_id,
			rows=len(rows),
			columns=col_count,
			cells=cells,
			source_region_id=region.id,
			bbox=region.bbox
		))

	return tables
