"""
Chat API Endpoint

Exposes the Copilot service via POST /api/v1/chat.
"""

import structlog
from fastapi import APIRouter, Depends

from app.utils.response import success_response, error_response
from app.core.dependencies import get_copilot_service
from app.copilot.copilot_service import CopilotService
from app.copilot.schemas import ChatRequest, ChatResponse, CitationOut

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("", response_model=dict)
async def chat(
    request: ChatRequest,
    copilot: CopilotService = Depends(get_copilot_service),
):
    """
    Submit a question to the AI Copilot.

    Supports conversational memory (via session_id).
    Retrieves knowledge context and generates a grounded answer with citations.
    """
    logger.info("api_chat_request", session_id=request.session_id)

    try:
        result = await copilot.ask(request)

        # Map internal models to output schemas
        citations_out = [
            CitationOut(
                document_id=c.document_id,
                document_name=c.document_name,
                section=c.section,
                page_number=c.page_number,
                asset_ids=c.asset_ids,
                confidence=c.confidence,
                excerpt=c.excerpt,
            )
            for c in result.citations
        ]

        response_data = ChatResponse(
            answer=result.answer,
            citations=citations_out,
            confidence=result.confidence,
            followup_questions=result.followup_questions,
            reasoning=result.reasoning,
            related_assets=result.related_assets,
            diagnostics=result.diagnostics,
        )

        return success_response(
            data=response_data.model_dump(),
            message="Chat response generated successfully",
        )

    except ValueError as ve:
        # Client error (e.g. invalid query)
        return error_response(
            message=str(ve),
            status_code=400,
            errors={"code": "INVALID_CHAT_REQUEST"},
        )
    except Exception as e:
        # Server error
        logger.error("api_chat_error", error=str(e), session_id=request.session_id)
        return error_response(
            message="An internal error occurred while generating the response.",
            status_code=500,
            errors={"code": "COPILOT_GENERATION_FAILED"},
        )
