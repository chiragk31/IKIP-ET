"""
Processing Service

Orchestrates the complete document processing pipeline for a single document.

Architecture:
    ProcessingHandler (Inngest event) → ProcessingService → [
        DocumentLoader,
        DocumentDetector,
        DoclingParser | SpreadsheetParser | TextParser | ImageParser,
        OCRService (if needed),
        CanonicalBuilder,
        StorageRepository (store canonical JSON),
        DocumentRepository (update status),
        InngestClient (emit document.processed),
    ]

Rules:
    - This service is the ONLY entry point for the processing pipeline.
    - It does NOT call Gemini or any AI model.
    - All external dependencies are injected.
    - Status is updated in the database at every major pipeline stage.
    - On failure: mark document as failed, log error, raise for Inngest retry.

Pipeline Stages (matching Processing Status enum):
    1. parsing     — Docling / text / spreadsheet extraction
    2. ocr         — PaddleOCR / pytesseract (only if needed)
    3. normalizing — Canonical builder merge + normalization
    4. completed   — Store result, emit event

Retry Policy:
    Inngest handles retries (3 attempts, exponential backoff).
    ProcessingService does not retry internally; it raises on failure.
"""

import io
import json
import time
from pathlib import Path
from typing import Optional
import structlog

from app.canonical.canonical_models import CanonicalDocument
from app.canonical.canonical_builder import CanonicalBuilder
from app.parser.document_loader import DocumentLoader
from app.parser.document_detector import DocumentDetector, ParserStrategy
from app.parser.docling_parser import DoclingParser
from app.ocr.ocr_service import OCRService
from app.repositories.document_repository import DocumentRepository
from app.repositories.storage_repository import StorageRepository
from app.events.inngest_client import InngestClient
from app.models.document import ProcessingJobModel
from app.utils.constants import DocumentStatus, ProcessingStage

logger = structlog.get_logger(__name__)

# Processed canonical JSON is stored at this path pattern in Supabase Storage
# CANONICAL_STORAGE_PATH = "processed/{document_id}/canonical.json"
CANONICAL_BUCKET = "documents"

# Pipeline version — increment when pipeline logic changes
PIPELINE_VERSION = "1.0.0"


class ProcessingService:
    """
    Orchestrates the full document processing pipeline.

    Injected dependencies let each stage be mocked in tests.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        storage_repo: StorageRepository,
        inngest: InngestClient,
    ) -> None:
        """
        Initialize ProcessingService with injected dependencies.

        Args:
            document_repo: For status updates and job tracking
            storage_repo: For downloading source files and storing canonical JSON
            inngest: For emitting document.processed event
        """
        self._document_repo = document_repo
        self._storage_repo = storage_repo
        self._inngest = inngest

        # Instantiate pipeline components (stateless, reusable)
        self._loader = DocumentLoader(storage_repo=storage_repo)
        self._detector = DocumentDetector()
        self._docling_parser = DoclingParser()
        self._ocr_service = OCRService()
        self._canonical_builder = CanonicalBuilder()

        logger.info("processing_service_initialized", pipeline_version=PIPELINE_VERSION)

    def process_document(
        self,
        document_id: str,
        storage_path: str,
        mime_type: str,
        file_size: int,
        original_filename: str,
        user_id: Optional[str] = None,
    ) -> CanonicalDocument:
        """
        Run the complete processing pipeline for a document.

        Args:
            document_id: Supabase document ID
            storage_path: Path in Supabase Storage bucket
            mime_type: MIME type from upload
            file_size: File size in bytes
            original_filename: Original upload filename
            user_id: User ID (optional)

        Returns:
            CanonicalDocument

        Raises:
            Exception: On any unrecoverable failure (triggers Inngest retry)
        """
        pipeline_start = time.time()

        logger.info(
            "processing_pipeline_start",
            document_id=document_id,
            filename=original_filename,
            mime_type=mime_type,
            file_size=file_size,
        )

        try:
            # ── Stage 1: Detection ──────────────────────────────────
            detection = self._detector.detect(
                mime_type=mime_type,
                original_filename=original_filename,
            )

            self._update_status(
                document_id=document_id,
                status=DocumentStatus.PROCESSING.value,
                stage=ProcessingStage.PARSING.value,
            )
            self._create_job(document_id=document_id, job_type=ProcessingStage.PARSING.value)

            # ── Stage 2: Parse ──────────────────────────────────────
            stage2_start = time.time()

            with self._loader.load(storage_path, original_filename) as local_path:
                canonical = self._parse(
                    local_path=local_path,
                    detection=detection,
                    document_id=document_id,
                    original_filename=original_filename,
                    storage_path=storage_path,
                    file_size=file_size,
                )

                # ── Stage 3: OCR (if needed) ────────────────────────
                if detection.needs_ocr or (canonical and canonical.warnings):
                    self._update_status(
                        document_id=document_id,
                        status=DocumentStatus.PROCESSING.value,
                        stage=ProcessingStage.OCR_RUNNING.value,
                    )
                    self._create_job(document_id=document_id, job_type=ProcessingStage.OCR_RUNNING.value)

                    ocr_results = self._run_ocr(
                        local_path=local_path,
                        detection=detection,
                        canonical=canonical,
                    )

                    # ── Stage 4: Merge + Normalize ──────────────────
                    self._update_status(
                        document_id=document_id,
                        status=DocumentStatus.PROCESSING.value,
                        stage=ProcessingStage.NORMALIZING.value,
                    )
                    canonical = self._canonical_builder.merge_ocr(canonical, ocr_results)
                else:
                    # No OCR needed — just finalize
                    self._update_status(
                        document_id=document_id,
                        status=DocumentStatus.PROCESSING.value,
                        stage=ProcessingStage.NORMALIZING.value,
                    )
                    canonical = self._canonical_builder.finalize(canonical)

            # ── Stage 5: Store canonical JSON ───────────────────────
            canonical_path = self._store_canonical(document_id, canonical)
            canonical.metadata.pipeline_version = PIPELINE_VERSION
            canonical.metadata.ocr_version = canonical.metadata.ocr_version or self._ocr_service.ocr_version

            total_duration = time.time() - pipeline_start
            canonical.processing_time_seconds = round(total_duration, 2)

            # ── Stage 6: Update status to completed ─────────────────
            self._update_status(
                document_id=document_id,
                status=DocumentStatus.COMPLETED.value,
                stage=ProcessingStage.COMPLETED.value,
            )

            # ── Stage 7: Emit document.processed event ──────────────
            self._inngest.send_event(
                event_name="document.processed",
                payload={
                    "document_id": document_id,
                    "canonical_storage_path": canonical_path,
                    "processing_time": canonical.processing_time_seconds,
                    "page_count": canonical.metadata.page_count,
                    "word_count": canonical.metadata.word_count,
                    "ocr_applied": canonical.ocr_applied,
                    "language": canonical.language,
                    "file_type": detection.file_type.value,
                    "user_id": user_id,
                },
                user_id=user_id,
            )

            logger.info(
                "processing_pipeline_complete",
                document_id=document_id,
                duration_seconds=canonical.processing_time_seconds,
                pages=canonical.metadata.page_count,
                words=canonical.metadata.word_count,
                ocr_applied=canonical.ocr_applied,
            )

            return canonical

        except Exception as e:
            total_duration = time.time() - pipeline_start
            logger.error(
                "processing_pipeline_failed",
                document_id=document_id,
                error=str(e),
                duration_seconds=round(total_duration, 2),
            )

            # Mark document as failed
            try:
                self._update_status(
                    document_id=document_id,
                    status=DocumentStatus.FAILED.value,
                    stage=None,
                )
            except Exception as status_err:
                logger.error(
                    "processing_status_update_failed",
                    document_id=document_id,
                    error=str(status_err),
                )

            raise

    # -----------------------------------------------------------
    # Private pipeline stage methods
    # -----------------------------------------------------------

    def _parse(
        self,
        local_path: str,
        detection,
        document_id: str,
        original_filename: str,
        storage_path: str,
        file_size: int,
    ) -> CanonicalDocument:
        """Run the appropriate parser based on detection result."""
        strategy = detection.parser

        if strategy == ParserStrategy.DOCLING:
            return self._docling_parser.parse(
                local_path=local_path,
                document_id=document_id,
                original_filename=original_filename,
                storage_path=storage_path,
                file_size=file_size,
                file_type=detection.file_type.value,
            )

        elif strategy == ParserStrategy.SPREADSHEET:
            return self._parse_spreadsheet(
                local_path=local_path,
                document_id=document_id,
                original_filename=original_filename,
                storage_path=storage_path,
                file_size=file_size,
                file_type=detection.file_type.value,
            )

        elif strategy == ParserStrategy.TEXT:
            return self._parse_text(
                local_path=local_path,
                document_id=document_id,
                original_filename=original_filename,
                storage_path=storage_path,
                file_size=file_size,
                file_type=detection.file_type.value,
            )

        elif strategy == ParserStrategy.IMAGE:
            # Images go straight to OCR — return empty canonical
            from app.canonical.canonical_models import DocumentMetadata, CanonicalPage
            return CanonicalDocument(
                document_id=document_id,
                original_filename=original_filename,
                storage_path=storage_path,
                metadata=DocumentMetadata(
                    file_type=detection.file_type.value,
                    file_size=file_size,
                    title=Path(original_filename).stem,
                ),
                pages=[CanonicalPage(page_number=1, text="")],
                full_text="",
            )

        else:
            raise ValueError(f"Unknown parser strategy: {strategy}")

    def _parse_spreadsheet(
        self,
        local_path: str,
        document_id: str,
        original_filename: str,
        storage_path: str,
        file_size: int,
        file_type: str,
    ) -> CanonicalDocument:
        """Parse XLSX/CSV into CanonicalDocument."""
        from app.canonical.canonical_models import (
            CanonicalPage, CanonicalTable, DocumentMetadata
        )

        text_lines = []
        tables = []

        try:
            if file_type == "csv":
                import csv
                with open(local_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                if rows:
                    headers = rows[0]
                    data_rows = rows[1:]
                    table = CanonicalTable(
                        page_number=1,
                        headers=headers,
                        rows=data_rows,
                        markdown=self._rows_to_markdown(headers, data_rows),
                    )
                    tables.append(table)
                    text_lines.append("\t".join(headers))
                    for row in data_rows:
                        text_lines.append("\t".join(row))

            elif file_type == "xlsx":
                import openpyxl
                wb = openpyxl.load_workbook(local_path, read_only=True, data_only=True)
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    rows = [[str(cell.value or "") for cell in row] for row in ws.iter_rows()]
                    if not rows:
                        continue
                    headers = rows[0]
                    data_rows = rows[1:]
                    table = CanonicalTable(
                        page_number=1,
                        caption=sheet_name,
                        headers=headers,
                        rows=data_rows,
                        markdown=self._rows_to_markdown(headers, data_rows),
                    )
                    tables.append(table)
                    text_lines.extend(["\t".join(row) for row in rows])

        except Exception as e:
            logger.error("spreadsheet_parse_failed", error=str(e))

        full_text = "\n".join(text_lines)
        return CanonicalDocument(
            document_id=document_id,
            original_filename=original_filename,
            storage_path=storage_path,
            metadata=DocumentMetadata(
                title=Path(original_filename).stem,
                file_type=file_type,
                file_size=file_size,
                page_count=1,
                table_count=len(tables),
            ),
            pages=[CanonicalPage(page_number=1, text=full_text)],
            tables=tables,
            full_text=full_text,
        )

    def _parse_text(
        self,
        local_path: str,
        document_id: str,
        original_filename: str,
        storage_path: str,
        file_size: int,
        file_type: str,
    ) -> CanonicalDocument:
        """Parse TXT file into CanonicalDocument."""
        from app.canonical.canonical_models import CanonicalPage, DocumentMetadata

        try:
            with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                full_text = f.read()
        except Exception as e:
            logger.error("text_parse_failed", error=str(e))
            full_text = ""

        return CanonicalDocument(
            document_id=document_id,
            original_filename=original_filename,
            storage_path=storage_path,
            metadata=DocumentMetadata(
                title=Path(original_filename).stem,
                file_type=file_type,
                file_size=file_size,
                page_count=1,
            ),
            pages=[CanonicalPage(page_number=1, text=full_text)],
            full_text=full_text,
        )

    def _run_ocr(
        self,
        local_path: str,
        detection,
        canonical: CanonicalDocument,
    ):
        """Run OCR based on document type and detection result."""
        from app.parser.document_detector import ParserStrategy

        try:
            if detection.parser == ParserStrategy.IMAGE:
                # Single image — read bytes and OCR
                with open(local_path, "rb") as f:
                    image_bytes = f.read()
                return [self._ocr_service.run_ocr_on_image(image_bytes, page_number=1)]

            elif detection.parser == ParserStrategy.DOCLING and canonical.warnings:
                # Scanned PDF — rasterize and OCR
                return self._ocr_service.run_ocr_on_pdf_pages(local_path)

            return []
        except Exception as e:
            logger.warning("ocr_failed_non_fatal", error=str(e))
            return []

    # def _store_canonical(self, document_id: str, canonical: CanonicalDocument) -> str:
    #     """
    #     Serialize canonical document to JSON and store in Supabase Storage.

    #     The processed output is stored SEPARATELY from the original upload.
    #     Path: processed/{document_id}/canonical.json

    #     Returns:
    #         Storage path of the stored canonical JSON
    #     """
    #     canonical_path = CANONICAL_STORAGE_PATH.format(document_id=document_id)

    #     try:
    #         canonical_json = json.dumps(canonical.to_dict(), ensure_ascii=False, indent=2)
    #         json_bytes = canonical_json.encode("utf-8")

    #         self._storage_repo.upload_file(
    #             file_content=json_bytes,
    #             original_filename=f"canonical_{document_id}.json",
    #             mime_type="application/json",
    #         )

    #         logger.info(
    #             "canonical_stored",
    #             document_id=document_id,
    #             path=canonical_path,
    #             size_bytes=len(json_bytes),
    #         )
    #         return canonical_path

    #     except Exception as e:
    #         logger.error(
    #             "canonical_storage_failed",
    #             document_id=document_id,
    #             error=str(e),
    #         )
    #         # Non-fatal: return empty path, downstream can reprocess
    #         return ""
    
   
    def _store_canonical(
        self,
        document_id: str,
        canonical: CanonicalDocument,
    ) -> str:
        """Store the canonical document and return its actual storage path."""
        try:
            canonical_json = json.dumps(
                canonical.to_dict(),
                ensure_ascii=False,
                indent=2,
            )
            json_bytes = canonical_json.encode("utf-8")

            result = self._storage_repo.upload_file(
                file_content=json_bytes,
                original_filename=f"canonical_{document_id}.json",
                mime_type="application/json",
            )

            # StorageRepository returns a dictionary, not a string.
            if not isinstance(result, dict) or not result.get("storage_path"):
                raise RuntimeError(
                    f"Storage upload did not return a valid path: {result!r}"
                )

            canonical_path = result["storage_path"]

            logger.info(
                "canonical_stored",
                document_id=document_id,
                path=canonical_path,
                bucket=result.get("bucket"),
                size_bytes=len(json_bytes),
            )

            return canonical_path

        except Exception as e:
            logger.error(
                "canonical_storage_failed",
                document_id=document_id,
                error=str(e),
            )
            raise


    def _update_status(
        self,
        document_id: str,
        status: str,
        stage: Optional[str] = None,
    ) -> None:
        """Update document processing status in Supabase."""
        try:
            self._document_repo.update_status(
                document_id=document_id,
                status=status,
                processing_stage=stage,
            )
        except Exception as e:
            logger.warning(
                "status_update_failed",
                document_id=document_id,
                status=status,
                error=str(e),
            )

    def _create_job(self, document_id: str, job_type: str) -> None:
        """Create a processing job record in Supabase."""
        try:
            job = ProcessingJobModel(
                document_id=document_id,
                job_type=job_type,
                status="running",
            )
            self._document_repo.create_processing_job(job)
        except Exception as e:
            logger.warning(
                "processing_job_create_failed",
                document_id=document_id,
                job_type=job_type,
                error=str(e),
            )

    @staticmethod
    def _rows_to_markdown(headers: list, rows: list) -> str:
        """Convert table headers and rows to Markdown table string."""
        if not headers:
            return ""
        sep = "| " + " | ".join(["---"] * len(headers)) + " |"
        header_row = "| " + " | ".join(str(h) for h in headers) + " |"
        data_rows = [
            "| " + " | ".join(str(cell) for cell in row) + " |"
            for row in rows[:100]  # Limit to 100 rows to avoid huge strings
        ]
        return "\n".join([header_row, sep] + data_rows)



