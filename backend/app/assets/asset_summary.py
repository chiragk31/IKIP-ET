"""
Asset Summary Builder

Builds the AssetNode from raw graph data and extracts related documents
from search results.

Per Assets.md §Asset Profile:
    Each asset should contain: Asset Name, Asset Tag, Asset Type,
    Manufacturer, Model, Serial Number, Installation Date, Location,
    Department, Status.

Per Assets.md §Asset Summary:
    The Asset Summary contains: Basic Information, Connected Assets,
    Active Procedures, Maintenance History, Inspection History,
    Compliance Overview, Related Documents.

Per Assets.md §Asset Identity:
    Priority: Asset Tag → Equipment ID → UUID.
    Display names are never used as identifiers.
"""

import structlog
from typing import Any, Dict, List, Optional

from app.assets.models import AssetNode, RelatedDocument
from app.search.models import ContextChunk

logger = structlog.get_logger(__name__)


class SummaryBuilder:
    """
    Builds AssetNode and RelatedDocument lists from raw data.

    Purpose:
        Extract structured asset properties from the raw graph node dict,
        and map HybridSearchService chunks to RelatedDocument objects.
    Input:
        - asset_360_data: Raw dict from GraphRepository.get_asset_360().
        - search_chunks: ContextChunk list from HybridSearchService.
    Output:
        - AssetNode with full provenance.
        - List[RelatedDocument] with traceability to chunk_id and page.
    """

    def build_asset_node(
        self,
        entity_id: str,
        asset_360_data: Optional[Dict[str, Any]],
    ) -> AssetNode:
        """
        Build an AssetNode from the raw graph asset_360 result.

        Property extraction follows the Asset Identity priority:
            Asset Tag → Equipment ID → stable entity_id.

        Args:
            entity_id: The validated asset entity_id (stable key).
            asset_360_data: Raw dict from GraphRepository.get_asset_360().
                            May be None if the node has just been located
                            but not yet returned (should not happen normally).

        Returns:
            AssetNode with all available provenance fields.
        """
        logger.info("summary_builder_build_node_start", entity_id=entity_id)

        if asset_360_data is None:
            # Return a minimal shell node — AssetService should have already
            # raised a 404 if the node truly doesn't exist, so this path
            # is only reached in edge cases.
            logger.warning("summary_builder_no_graph_data", entity_id=entity_id)
            return AssetNode(entity_id=entity_id)

        # The 'a' key in asset_360_data is the raw asset node from Neo4j
        # (returned as a dict via record.data(), which calls Node.data())
        raw_node = asset_360_data.get("a") or {}

        # If the result dict itself is flat (node properties directly in dict)
        # fall back to treating the whole dict as the node
        if not raw_node and "entity_id" in asset_360_data:
            raw_node = asset_360_data

        if isinstance(raw_node, dict):
            node_props = raw_node
        else:
            # Neo4j Node object — convert to dict
            try:
                node_props = dict(raw_node)
            except Exception:
                node_props = {}

        # Extract structured properties with fallbacks
        name = node_props.get("name", "")
        aliases_raw = node_props.get("aliases", [])
        aliases = list(aliases_raw) if isinstance(aliases_raw, (list, tuple)) else []

        # Asset identity: prefer explicit tag fields, fall back to entity_id
        asset_tag = self._extract_first(
            node_props, ["asset_tag", "tag", "equipment_tag"]
        )
        equipment_id = self._extract_first(
            node_props, ["equipment_id", "eq_id", "equipment_number"]
        )

        # Location and department
        location = self._extract_first(
            node_props, ["location", "plant", "site", "area"]
        )
        department = self._extract_first(
            node_props, ["department", "dept", "unit"]
        )

        # Technical properties (best-effort from graph data)
        manufacturer = self._extract_first(node_props, ["manufacturer", "make", "vendor"])
        model = self._extract_first(node_props, ["model", "model_number"])
        serial_number = self._extract_first(node_props, ["serial_number", "serial", "sn"])
        installation_date = self._extract_first(
            node_props, ["installation_date", "commissioned_date", "install_date"]
        )
        status = self._extract_first(node_props, ["status", "asset_status", "condition"])

        # Provenance
        source_document = node_props.get("source_document", "")
        confidence = self._safe_float(node_props.get("confidence", 0.0))
        created_at = node_props.get("created_at", "")
        entity_type = node_props.get("entity_type", "Asset")

        # Capture any remaining properties in raw_properties for transparency
        structured_keys = {
            "entity_id", "name", "aliases", "asset_tag", "tag", "equipment_tag",
            "equipment_id", "eq_id", "equipment_number", "location", "plant",
            "site", "area", "department", "dept", "unit", "manufacturer",
            "make", "vendor", "model", "model_number", "serial_number",
            "serial", "sn", "installation_date", "commissioned_date",
            "install_date", "status", "asset_status", "condition",
            "source_document", "confidence", "created_at", "entity_type",
            "extraction_version", "properties",
        }
        raw_properties = {
            k: v for k, v in node_props.items() if k not in structured_keys
        }

        node = AssetNode(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            label="Asset",
            asset_tag=asset_tag,
            equipment_id=equipment_id,
            manufacturer=manufacturer,
            model=model,
            serial_number=serial_number,
            installation_date=installation_date,
            location=location,
            department=department,
            status=status,
            aliases=aliases,
            source_document=source_document,
            confidence=confidence,
            created_at=created_at,
            raw_properties=raw_properties,
        )

        logger.info(
            "summary_builder_build_node_complete",
            entity_id=entity_id,
            name=name,
            source_document=source_document,
        )
        return node

    def build_related_documents(
        self,
        chunks: List[ContextChunk],
    ) -> List[RelatedDocument]:
        """
        Map HybridSearchService ContextChunk results to RelatedDocument objects.

        Per Assets.md §Search Integration:
            "The Asset module never performs vector search directly."
        All chunks originate from HybridSearchService — this method only
        converts the results to the Asset module's internal type.

        Per Assets.md §Explainability:
            Each RelatedDocument carries chunk_id and confidence so users
            can trace exactly which chunk matched and with what score.

        Args:
            chunks: ContextChunk list from HybridSearchService result.

        Returns:
            List[RelatedDocument] deduplicated by document_id + chunk_id.
        """
        logger.info("summary_builder_documents_start", chunk_count=len(chunks))

        docs: List[RelatedDocument] = []
        seen_chunk_ids: set = set()

        for chunk in chunks:
            if chunk.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk.chunk_id)

            # Build a concise excerpt (first 300 chars of chunk text)
            excerpt = (chunk.text or "")[:300]
            if len(chunk.text or "") > 300:
                excerpt += "…"

            # Extract document_name from metadata if available
            doc_name = ""
            if chunk.citation:
                doc_name = chunk.citation.document_name or ""

            confidence = chunk.score
            if chunk.citation:
                confidence = max(confidence, chunk.citation.confidence)

            doc = RelatedDocument(
                document_id=chunk.document_id,
                document_name=doc_name,
                document_type=chunk.document_type,
                section=chunk.section,
                page_number=chunk.page_number,
                excerpt=excerpt,
                chunk_id=chunk.chunk_id,
                confidence=confidence,
                source_type="semantic",
            )
            docs.append(doc)

        logger.info(
            "summary_builder_documents_complete",
            documents_built=len(docs),
        )
        return docs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_first(props: Dict[str, Any], keys: List[str]) -> Optional[str]:
        """
        Return the first non-empty value found under any of the given keys.

        Args:
            props: Property dict to search.
            keys: List of candidate keys in priority order.

        Returns:
            First matching string value, or None.
        """
        for key in keys:
            val = props.get(key)
            if val and str(val).strip():
                return str(val).strip()
        return None

    @staticmethod
    def _safe_float(val: Any) -> float:
        """Safely convert to float, returning 0.0 on failure."""
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0
