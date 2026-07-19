"""
OCR Service

Extracts text from images and scanned documents.

Primary engine: PaddleOCR
Fallback engine: pytesseract (if PaddleOCR fails due to numpy ABI mismatch)

Architecture:
    ProcessingService → OCRService → ImagePreprocessor → [PaddleOCR | pytesseract]

Rules:
    - OCR is ONLY applied to image files and scanned PDFs.
    - For text-based PDFs/DOCX, OCR is never invoked.
    - Failures in OCR are non-fatal: return empty text with a warning.
    - Never call Gemini or any AI service here.
    - Supports multi-page documents: returns one OCRResult per page.

PaddleOCR Note:
    The installed PaddleOCR has a numpy 2.x ABI conflict (paddlepaddle compiled
    against numpy 1.x). This service catches that at import and uses pytesseract
    as the fallback. If neither is available, it falls back to Pillow-only
    (empty text with warning).
"""

import io
import time
from dataclasses import dataclass
from typing import List, Optional
import structlog

from app.ocr.image_preprocessor import ImagePreprocessor

logger = structlog.get_logger(__name__)


@dataclass
class OCRPageResult:
    """
    OCR result for a single page or image.

    Args:
        page_number: 1-indexed page number (1 for standalone images)
        text: Extracted text
        confidence: Average confidence score (0–1), or None if not available
        engine: OCR engine used ("paddleocr", "pytesseract", or "none")
    """
    page_number: int
    text: str
    confidence: Optional[float] = None
    engine: str = "none"


def _try_import_paddleocr():
    """Try to import PaddleOCR, return None if numpy ABI conflict."""
    try:
        from paddleocr import PaddleOCR
        return PaddleOCR
    except (ImportError, RuntimeError, AttributeError) as e:
        logger.warning(
            "paddleocr_unavailable",
            error=str(e),
            fallback="Using pytesseract as OCR engine",
        )
        return None


def _try_import_tesseract():
    """Try to import pytesseract, return None if not available."""
    try:
        import pytesseract
        return pytesseract
    except ImportError:
        logger.warning(
            "pytesseract_unavailable",
            note="No OCR engine available; extracted text will be empty",
        )
        return None


class OCRService:
    """
    Extracts text from images using PaddleOCR with pytesseract fallback.

    Auto-detects available OCR engine at startup and uses the best one.
    All callers receive the same OCRPageResult interface regardless of engine.
    """

    def __init__(self) -> None:
        self._preprocessor = ImagePreprocessor()
        self._engine = "none"
        self._paddle_ocr = None
        self._tesseract = None
        self._ocr_version = "none"

        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Try PaddleOCR, fall back to pytesseract, then None."""
        PaddleOCR = _try_import_paddleocr()
        if PaddleOCR is not None:
            try:
                # Initialize with English; use_angle_cls detects rotated text
                self._paddle_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                    show_log=False,
                )
                self._engine = "paddleocr"
                try:
                    import paddleocr
                    self._ocr_version = getattr(paddleocr, "__version__", "unknown")
                except Exception:
                    self._ocr_version = "unknown"
                logger.info("ocr_engine_ready", engine="paddleocr", version=self._ocr_version)
                return
            except Exception as e:
                logger.warning("paddleocr_init_failed", error=str(e))

        tesseract = _try_import_tesseract()
        if tesseract is not None:
            self._tesseract = tesseract
            self._engine = "pytesseract"
            try:
                self._ocr_version = tesseract.get_tesseract_version()
            except Exception:
                self._ocr_version = "unknown"
            logger.info("ocr_engine_ready", engine="pytesseract", version=str(self._ocr_version))
            return

        logger.warning(
            "ocr_engine_unavailable",
            note="No OCR engine could be initialized. Image documents will have empty text.",
        )

    @property
    def ocr_version(self) -> Optional[str]:
        """Return OCR engine version string for metadata storage."""
        if self._engine == "none":
            return None
        return f"{self._engine}:{self._ocr_version}"

    def run_ocr_on_image(
        self,
        image_bytes: bytes,
        page_number: int = 1,
    ) -> OCRPageResult:
        """
        Run OCR on a single image.

        Args:
            image_bytes: Raw image bytes
            page_number: Page number for result attribution

        Returns:
            OCRPageResult with extracted text
        """
        start_time = time.time()

        # Preprocess the image
        processed_bytes = self._preprocessor.preprocess(image_bytes)

        if self._engine == "paddleocr":
            result = self._run_paddleocr(processed_bytes, page_number)
        elif self._engine == "pytesseract":
            result = self._run_tesseract(processed_bytes, page_number)
        else:
            result = OCRPageResult(
                page_number=page_number,
                text="",
                engine="none",
            )

        duration = time.time() - start_time
        logger.info(
            "ocr_page_complete",
            page=page_number,
            engine=result.engine,
            chars=len(result.text),
            duration_ms=round(duration * 1000),
        )
        return result

    def run_ocr_on_pdf_pages(
        self,
        local_pdf_path: str,
    ) -> List[OCRPageResult]:
        """
        Run OCR on a scanned PDF by converting pages to images first.

        Uses pdf2image (Poppler) to rasterize pages, then OCRs each page.

        Args:
            local_pdf_path: Path to the local PDF file

        Returns:
            List of OCRPageResult, one per page
        """
        results: List[OCRPageResult] = []

        try:
            from pdf2image import convert_from_path

            logger.info("ocr_pdf_start", path=local_pdf_path)
            pil_images = convert_from_path(local_pdf_path, dpi=300)

            for page_idx, pil_image in enumerate(pil_images):
                buf = io.BytesIO()
                pil_image.save(buf, format="PNG")
                page_bytes = buf.getvalue()

                page_result = self.run_ocr_on_image(
                    image_bytes=page_bytes,
                    page_number=page_idx + 1,
                )
                results.append(page_result)

        except ImportError:
            logger.warning(
                "pdf2image_unavailable",
                note="Cannot rasterize PDF for OCR. Install: pip install pdf2image",
            )
            results.append(OCRPageResult(
                page_number=1,
                text="",
                engine="none",
            ))
        except Exception as e:
            logger.error("ocr_pdf_failed", error=str(e))
            results.append(OCRPageResult(
                page_number=1,
                text="",
                engine="none",
            ))

        return results

    def _run_paddleocr(self, image_bytes: bytes, page_number: int) -> OCRPageResult:
        """Run PaddleOCR on preprocessed image bytes."""
        try:
            import numpy as np
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_array = np.array(img)

            result = self._paddle_ocr.ocr(img_array, cls=True)

            lines = []
            confidences = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_info = line[1]
                        if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                            text, conf = text_info[0], text_info[1]
                            lines.append(str(text))
                            if isinstance(conf, (int, float)):
                                confidences.append(float(conf))

            avg_confidence = sum(confidences) / len(confidences) if confidences else None
            return OCRPageResult(
                page_number=page_number,
                text="\n".join(lines),
                confidence=avg_confidence,
                engine="paddleocr",
            )

        except Exception as e:
            logger.error("paddleocr_run_failed", error=str(e))
            return OCRPageResult(page_number=page_number, text="", engine="paddleocr_error")

    def _run_tesseract(self, image_bytes: bytes, page_number: int) -> OCRPageResult:
        """Run pytesseract on preprocessed image bytes."""
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            text = self._tesseract.image_to_string(img, lang="eng")
            return OCRPageResult(
                page_number=page_number,
                text=text.strip(),
                engine="pytesseract",
            )
        except Exception as e:
            logger.error("tesseract_run_failed", error=str(e))
            return OCRPageResult(page_number=page_number, text="", engine="tesseract_error")
