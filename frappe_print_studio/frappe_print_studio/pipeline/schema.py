# Pydantic data schemas/contracts for pipeline boundaries
from pydantic import BaseModel, Field
from typing import List, Tuple, Dict, Any, Optional

class OCRBlock(BaseModel):
	text: str
	bbox: Tuple[float, float, float, float]  # (xmin, ymin, xmax, ymax)
	confidence: float

class OCRResult(BaseModel):
	blocks: List[OCRBlock] = []

class LayoutRegion(BaseModel):
	id: str
	region_type: str  # e.g., 'header', 'table', 'totals', 'footer', 'signature', 'text'
	bbox: Tuple[float, float, float, float]
	contained_blocks: List[OCRBlock] = []
	confidence: float = 1.0

class TableCell(BaseModel):
	row_index: int
	col_index: int
	row_span: int = 1
	col_span: int = 1
	text: str
	bbox: Optional[Tuple[float, float, float, float]] = None

class TableStructure(BaseModel):
	id: str
	rows: int
	columns: int
	cells: List[TableCell] = []
	source_region_id: Optional[str] = None
	bbox: Tuple[float, float, float, float]

class IntermediateDocumentSchema(BaseModel):
	regions: List[LayoutRegion] = []
	tables: List[TableStructure] = []
	raw_ocr: OCRResult
	metadata: Dict[str, Any] = {}

class DocTypeFieldMetadata(BaseModel):
	fieldname: str
	label: str
	fieldtype: str
	options: Optional[str] = None
	reqd: int = 0

class DocTypeChildTableMetadata(BaseModel):
	fieldname: str
	label: str
	options: str  # DocType of the child table
	fields: List[DocTypeFieldMetadata] = []

class DocTypeMetadata(BaseModel):
	doctype: str
	fields: List[DocTypeFieldMetadata] = []
	child_tables: List[DocTypeChildTableMetadata] = []

class FieldMapping(BaseModel):
	detected_label: str
	fieldname: str
	confidence: float
	mapping_method: str  # 'exact', 'fuzzy', 'semantic', 'manual'
	is_override: bool = False

class PrintFormatOutput(BaseModel):
	html: str
	css: str
	jinja: str
	unresolved_fields: List[str] = []
