"""
Query Rewriter

Expands ambiguous queries using the LLM to improve semantic recall.

Purpose:
    Given a short or ambiguous natural language query, rewrite it to
    include synonyms, full terminology, and multiple angles of search,
    producing an expanded query string for the vector embedding model.

Input:
    ProcessedQuery (from QueryProcessor).

Output:
    ProcessedQuery with `expanded_query` field updated.
"""

import json
import structlog
from typing import Dict, Any

from app.search.models import ProcessedQuery
from app.ai.llm_service import LLMService

logger = structlog.get_logger(__name__)


class QueryRewriter:
    """
    Expands search queries using LLMService.

    Purpose:
        Overcome semantic vocabulary mismatch by enriching the query.
    Input:
        ProcessedQuery object.
    Output:
        ProcessedQuery object with expanded_query populated.
    """

    def __init__(self, llm_service: LLMService) -> None:
        """
        Initialize QueryRewriter.

        Args:
            llm_service: LLM gateway for generating the rewrite.
        """
        self._llm = llm_service
        logger.info("query_rewriter_initialized")

    async def rewrite(self, query: ProcessedQuery) -> ProcessedQuery:
        """
        Rewrite the query via LLM.

        Args:
            query: ProcessedQuery to rewrite.

        Returns:
            Updated ProcessedQuery.
        """
        logger.info("query_rewriter_start", query=query.normalized_query)

        # Skip rewriting for extremely long queries — likely already detailed
        if len(query.normalized_query) > 200:
            logger.info("query_rewriter_skipped_length")
            return query

        try:
            # We use the existing query_rewrite.md prompt
            response = await self._llm.generate(
                prompt_name="query_rewrite",
                variables={"question": query.normalized_query},
            )

            # The generate() method returns a tuple: (result_dict, token_usage)
            if isinstance(response, tuple):
                data = response[0]
            else:
                data = response

            queries = data.get("search_queries", [])
            if queries:
                expanded = f"{query.normalized_query} " + " ".join(queries)
                query.expanded_query = expanded
                logger.info("query_rewriter_success", expanded=expanded)
                return query

            logger.warning("query_rewriter_parse_failed", data=data)
            return query

        except Exception as e:
            logger.warning("query_rewriter_failed", error=str(e))
            # Fall back to original query gracefully — search must not fail
            # just because the rewriter failed.
            return query
