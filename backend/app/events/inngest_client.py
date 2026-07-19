"""
Inngest Event Client

Thin wrapper around the Inngest HTTP API for sending events.

Architecture:
    UploadService → InngestClient → Inngest API → Processing Pipeline

Rules:
    - Never start the processing pipeline directly from UploadService.
    - Always emit events; never invoke downstream modules directly.
    - Event payload must include document_id, storage_path, mime_type.

Event names match InngestEvent enum in utils/constants.py.

Inngest Dev Mode:
    Run locally: npx inngest-cli@latest dev
    Events will appear at http://localhost:8288
"""

import json
from typing import Any, Dict, Optional
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Inngest Event API endpoint
INNGEST_EVENT_URL = "https://inn.gs/e/{event_key}"
INNGEST_LOCAL_URL = "http://127.0.0.1:8288/e/{event_key}"


class InngestClient:
    """
    Client for sending events to the Inngest workflow engine.

    Wraps the Inngest HTTP event API.
    In development, events are sent to the local Inngest Dev Server.
    In production, events are sent to the Inngest Cloud API.

    This class is used ONLY for sending events (outbound).
    Inngest function handlers are defined separately in events/*.py files.
    """

    def __init__(self, event_key: str, is_development: bool = True) -> None:
        """
        Initialize the Inngest client.

        Args:
            event_key: Inngest event key for authentication
            is_development: If True, send to local dev server; else to Inngest Cloud
        """
        self._event_key = event_key
        self._is_development = is_development

        if is_development:
            self._base_url = INNGEST_LOCAL_URL.format(event_key=event_key)
        else:
            self._base_url = INNGEST_EVENT_URL.format(event_key=event_key)

        logger.info(
            "inngest_client_initialized",
            mode="development" if is_development else "production",
            url=self._base_url,
        )

    def send_event(
        self,
        event_name: str,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Send an event to Inngest.

        Args:
            event_name: Inngest event name (e.g., "document.uploaded")
            payload: Event data dict
            user_id: Optional user ID for event attribution

        Returns:
            True if event was sent successfully, False otherwise

        Note:
            Failures are logged but NOT raised — upload should never fail
            due to an Inngest connectivity issue. The document is already
            saved; reprocessing can be triggered manually.
        """
        logger.info(
            "inngest_event_send_start",
            event_name=event_name,
            payload_keys=list(payload.keys()),
        )

        event_body = {
            "name": event_name,
            "data": payload,
        }

        if user_id:
            event_body["user"] = {"id": user_id}

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    self._base_url,
                    json=event_body,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code in (200, 201):
                    logger.info(
                        "inngest_event_send_success",
                        event_name=event_name,
                        status_code=response.status_code,
                    )
                    return True
                else:
                    logger.warning(
                        "inngest_event_send_unexpected_status",
                        event_name=event_name,
                        status_code=response.status_code,
                        response_text=response.text[:200],
                    )
                    return False

        except httpx.ConnectError:
            # Inngest Dev Server not running — log and continue
            logger.warning(
                "inngest_event_send_connection_error",
                event_name=event_name,
                note="Inngest Dev Server not reachable. Start with: npx inngest-cli@latest dev",
            )
            return False

        except Exception as e:
            logger.error(
                "inngest_event_send_failed",
                event_name=event_name,
                error=str(e),
            )
            return False

    def send_document_uploaded_event(
        self,
        document_id: str,
        storage_path: str,
        mime_type: str,
        file_size: int,
        original_filename: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Emit the `document.uploaded` event to trigger the AI pipeline.

        This is the primary handoff point from the upload module to Epic 2.
        The processing pipeline subscribes to this event and begins parsing.

        Args:
            document_id: Supabase document ID
            storage_path: Full path in Supabase Storage bucket
            mime_type: MIME type of the uploaded file
            file_size: File size in bytes
            original_filename: Original filename for display
            user_id: Uploader user ID (optional until auth is implemented)

        Returns:
            True if event was sent successfully
        """
        payload = {
            "document_id": document_id,
            "storage_path": storage_path,
            "mime_type": mime_type,
            "file_size": file_size,
            "original_filename": original_filename,
            "user_id": user_id,
        }

        return self.send_event(
            event_name="document.uploaded",
            payload=payload,
            user_id=user_id,
        )

    def send_document_processed_event(
        self,
        document_id: str,
        canonical_storage_path: str,
        processing_time: float,
        page_count: int = 0,
        word_count: int = 0,
        ocr_applied: bool = False,
        language: str = "en",
        file_type: str = "",
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Emit the `document.processed` event to trigger Epic 3 (AI Extraction).

        This is the handoff from Epic 2 to Epic 3.
        The AI Knowledge Extraction service subscribes to this event.

        Args:
            document_id: Supabase document ID
            canonical_storage_path: Storage path of the canonical JSON
            processing_time: Processing duration in seconds
            page_count: Number of pages extracted
            word_count: Word count of full text
            ocr_applied: Whether OCR was applied
            language: Detected document language
            file_type: Source file type
            user_id: User ID (optional)

        Returns:
            True if event was sent successfully
        """
        payload = {
            "document_id": document_id,
            "canonical_storage_path": canonical_storage_path,
            "processing_time": processing_time,
            "page_count": page_count,
            "word_count": word_count,
            "ocr_applied": ocr_applied,
            "language": language,
            "file_type": file_type,
            "user_id": user_id,
        }

        return self.send_event(
            event_name="document.processed",
            payload=payload,
            user_id=user_id,
        )