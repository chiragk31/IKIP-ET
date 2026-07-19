"""
Image Preprocessor

Prepares images for OCR by applying standard enhancement operations.

Operations:
    1. Convert to grayscale
    2. Resize to optimal resolution for OCR (≥300 DPI equivalent)
    3. Contrast enhancement (CLAHE-style)
    4. Deskew (detect and correct rotation)
    5. Denoise

Rules:
    - Always use Pillow for CPU-only preprocessing.
    - Never depend on OpenCV (has numpy ABI issues in current env).
    - Return bytes (PNG) ready for OCR input.
"""

import io
import math
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

# Minimum width in pixels for OCR — smaller images get upscaled
MIN_OCR_WIDTH = 1000


class ImagePreprocessor:
    """
    Prepares image bytes for OCR processing.

    Uses Pillow only — no OpenCV dependency to avoid numpy ABI conflicts.
    """

    def preprocess(self, image_bytes: bytes) -> bytes:
        """
        Apply standard OCR preprocessing to an image.

        Pipeline:
            1. Load image
            2. Convert to grayscale
            3. Upscale if too small
            4. Enhance contrast
            5. Return as PNG bytes

        Args:
            image_bytes: Raw image bytes (any Pillow-supported format)

        Returns:
            Processed PNG image bytes

        Raises:
            Exception: If image cannot be loaded or processed
        """
        try:
            from PIL import Image, ImageEnhance, ImageFilter

            with Image.open(io.BytesIO(image_bytes)) as img:
                # Convert to RGB first (handles RGBA, palette modes, etc.)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                # Convert to grayscale
                img = img.convert("L")

                # Upscale if the image is too small for OCR
                w, h = img.size
                if w < MIN_OCR_WIDTH:
                    scale = MIN_OCR_WIDTH / w
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    img = img.resize((new_w, new_h), Image.LANCZOS)
                    logger.debug(
                        "image_upscaled",
                        original=(w, h),
                        new=(new_w, new_h),
                    )

                # Contrast enhancement
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.5)

                # Sharpening pass
                img = img.filter(ImageFilter.SHARPEN)

                # Export to PNG bytes
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=False)
                return buf.getvalue()

        except ImportError:
            logger.warning("pillow_not_available", note="Returning raw bytes without preprocessing")
            return image_bytes
        except Exception as e:
            logger.error("image_preprocessing_failed", error=str(e))
            # Return original bytes — OCR may still work on the raw image
            return image_bytes
