"""
Platform Constants and Enumerations

Shared constants used across all backend modules.
Never hardcode these values elsewhere — always import from here.
"""

from enum import Enum


# -----------------------------------------------
# Document Processing
# -----------------------------------------------

class DocumentStatus(str, Enum):
    """Processing status for uploaded documents."""
    QUEUED = "queued"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSING = "parsing"
    OCR_RUNNING = "ocr_running"
    EXTRACTING = "extracting"
    BUILDING_GRAPH = "building_graph"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    SUMMARIZING = "summarizing"
    COMPLIANCE_CHECK = "compliance_check"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    TXT = "txt"
    CSV = "csv"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    TIFF = "tiff"


class ProcessingJobType(str, Enum):
    """Types of background processing jobs."""
    PARSING = "parsing"
    OCR = "ocr"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"
    ONTOLOGY_UPDATE = "ontology_update"
    GRAPH_BUILD = "graph_build"
    EMBEDDING_GENERATION = "embedding_generation"
    SUMMARIZATION = "summarization"
    COMPLIANCE_ANALYSIS = "compliance_analysis"


class ProcessingStage(str, Enum):
    """Pipeline stage labels used in document.processing_stage column."""
    PARSING = "parsing"
    OCR_RUNNING = "ocr_running"
    NORMALIZING = "normalizing"
    EXTRACTING = "extracting"
    BUILDING_GRAPH = "building_graph"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    SUMMARIZING = "summarizing"
    COMPLIANCE_CHECK = "compliance_check"
    COMPLETED = "completed"


# -----------------------------------------------
# Ontology
# -----------------------------------------------

class EntityType(str, Enum):
    """Core ontology entity types (predefined, stable)."""
    DOCUMENT = "Document"
    ASSET = "Asset"
    PERSON = "Person"
    ORGANIZATION = "Organization"
    LOCATION = "Location"
    PROCEDURE = "Procedure"
    EVENT = "Event"
    MEASUREMENT = "Measurement"
    RISK = "Risk"
    FAILURE = "Failure"
    REGULATION = "Regulation"
    CONCEPT = "Concept"  # Dynamic ontology node


class RelationshipType(str, Enum):
    """Core relationship types in the knowledge graph."""
    MENTIONS = "MENTIONS"
    HAS_FAILURE = "HAS_FAILURE"
    LOCATED_IN = "LOCATED_IN"
    PERFORMED = "PERFORMED"
    HAS_MEASUREMENT = "HAS_MEASUREMENT"
    REFERENCES = "REFERENCES"
    CONNECTED_TO = "CONNECTED_TO"
    RELATED_TO = "RELATED_TO"
    CAUSED_BY = "CAUSED_BY"
    USES = "USES"
    REQUIRES = "REQUIRES"
    MITIGATED_BY = "MITIGATED_BY"
    RECORDED_FOR = "RECORDED_FOR"
    INVOLVES = "INVOLVES"
    OWNS = "OWNS"
    GENERATED_FROM = "GENERATED_FROM"
    PART_OF = "PART_OF"


# -----------------------------------------------
# Inngest Events
# -----------------------------------------------

class InngestEvent(str, Enum):
    """Event names for Inngest workflow triggers."""
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PARSED = "document.parsed"
    OCR_COMPLETED = "ocr.completed"
    ENTITIES_EXTRACTED = "entities.extracted"
    ONTOLOGY_UPDATED = "ontology.updated"
    GRAPH_UPDATED = "graph.updated"
    EMBEDDINGS_GENERATED = "embeddings.generated"
    SUMMARY_GENERATED = "summary.generated"
    DOCUMENT_READY = "document.ready"


# -----------------------------------------------
# File Constraints
# -----------------------------------------------

SUPPORTED_MIME_TYPES = {
    "application/pdf": DocumentType.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentType.PPTX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.XLSX,
    "text/plain": DocumentType.TXT,
    "text/csv": DocumentType.CSV,
    "image/png": DocumentType.PNG,
    "image/jpeg": DocumentType.JPEG,
    "image/tiff": DocumentType.TIFF,
}

SUPPORTED_EXTENSIONS = {
    ".pdf": DocumentType.PDF,
    ".docx": DocumentType.DOCX,
    ".pptx": DocumentType.PPTX,
    ".xlsx": DocumentType.XLSX,
    ".txt": DocumentType.TXT,
    ".csv": DocumentType.CSV,
    ".png": DocumentType.PNG,
    ".jpg": DocumentType.JPG,
    ".jpeg": DocumentType.JPEG,
    ".tiff": DocumentType.TIFF,
}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


# -----------------------------------------------
# Chunking
# -----------------------------------------------

CHUNK_SIZE_TOKENS = 1000       # Target chunk size in tokens
CHUNK_OVERLAP_TOKENS = 200     # Overlap between consecutive chunks
MIN_CHUNK_SIZE_TOKENS = 800    # Minimum acceptable chunk size
MAX_CHUNK_SIZE_TOKENS = 1200   # Maximum acceptable chunk size


# -----------------------------------------------
# Confidence Thresholds
# -----------------------------------------------

MIN_ENTITY_CONFIDENCE = 0.5    # Entities below this are flagged for review
MIN_RELATIONSHIP_CONFIDENCE = 0.6
HIGH_CONFIDENCE_THRESHOLD = 0.9


# -----------------------------------------------
# Supabase Storage
# -----------------------------------------------

STORAGE_BUCKET_DOCUMENTS = "documents"


# -----------------------------------------------
# API
# -----------------------------------------------

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_SEARCH_TOP_K = 10
MAX_SEARCH_TOP_K = 50
