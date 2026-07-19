"""
Pinecone Client Wrapper

Repository-level abstraction over the Pinecone Python SDK.
All vector database operations must go through this client.

Responsibilities:
- Index connection management
- Vector upsert (embeddings storage)
- Vector query (semantic search)
- Health verification

Rules:
- Only chunks should be embedded, never full documents.
- Every vector must include full citation metadata.
- Chunk size: 800-1200 tokens with 150-250 token overlap.
"""

from typing import Optional, Any, Dict, List
import structlog

logger = structlog.get_logger(__name__)


class PineconeClient:
    """
    Pinecone client wrapper.

    Manages the connection to Pinecone and provides
    methods for upsert and query operations.
    """

    def __init__(self, api_key: str, index_name: str) -> None:
        """
        Initialize the Pinecone client.

        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index to use
        """
        self.api_key = api_key
        self.index_name = index_name
        self._client = None
        self._index = None
        logger.info("pinecone_client_init", index_name=index_name)

    def _get_client(self):
        """
        Get or create Pinecone client (lazy initialization).

        Returns:
            Pinecone: Client instance
        """
        if self._client is None:
            try:
                from pinecone import Pinecone
                self._client = Pinecone(api_key=self.api_key)
            except ImportError:
                logger.warning("pinecone_sdk_not_installed")
                raise ImportError("pinecone-client package not installed. Run: pip install pinecone-client")
        return self._client

    def _get_index(self):
        """
        Get or create the Pinecone index connection.

        Returns:
            Index: Pinecone index instance
        """
        if self._index is None:
            client = self._get_client()
            self._index = client.Index(self.index_name)
        return self._index

    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = "",
    ) -> Dict[str, Any]:
        """
        Upsert vectors into the Pinecone index.

        Args:
            vectors: List of vector dicts with id, values, and metadata
            namespace: Optional namespace for multi-tenancy

        Returns:
            Upsert response

        Example vector format:
            {
                "id": "chunk_doc123_001",
                "values": [0.1, 0.2, ...],  # embedding
                "metadata": {
                    "chunk_id": "chunk_doc123_001",
                    "document_id": "doc123",
                    "page_number": 4,
                    "section": "Maintenance History",
                    "document_type": "maintenance_report",
                    "asset_ids": ["P101", "C4"],
                    "keywords": ["bearing", "overheating"],
                    "language": "en",
                    "created_at": "2026-07-19T00:00:00Z"
                }
            }
        """
        index = self._get_index()
        response = index.upsert(vectors=vectors, namespace=namespace)
        logger.info(
            "pinecone_vectors_upserted",
            count=len(vectors),
            namespace=namespace,
        )
        return response

    def query_vectors(
        self,
        vector: List[float],
        top_k: int = 10,
        namespace: str = "",
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Query the Pinecone index for similar vectors.

        Args:
            vector: Query embedding vector
            top_k: Number of results to return
            namespace: Optional namespace
            filter: Optional metadata filter
            include_metadata: Whether to include chunk metadata

        Returns:
            Query results with matches and scores
        """
        index = self._get_index()
        response = index.query(
            vector=vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter,
            include_metadata=include_metadata,
        )
        logger.info(
            "pinecone_query_executed",
            top_k=top_k,
            matches_found=len(response.get("matches", [])),
        )
        return response

    def delete_vectors(
        self,
        ids: List[str],
        namespace: str = "",
    ) -> Dict[str, Any]:
        """
        Delete vectors by ID.

        Args:
            ids: List of vector IDs to delete
            namespace: Optional namespace

        Returns:
            Delete response
        """
        index = self._get_index()
        response = index.delete(ids=ids, namespace=namespace)
        logger.info("pinecone_vectors_deleted", count=len(ids))
        return response

    def health_check(self) -> Dict[str, Any]:
        """
        Verify Pinecone connection is functional.

        Returns:
            Dict with status and details

        Raises:
            Exception: If connection fails
        """
        try:
            client = self._get_client()
            # List indexes to verify connectivity
            indexes = client.list_indexes()
            index_names = [idx.name for idx in indexes]
            index_exists = self.index_name in index_names
            return {
                "status": "up",
                "index_name": self.index_name,
                "index_exists": index_exists,
                "available_indexes": index_names,
            }
        except Exception as e:
            logger.error("pinecone_health_check_failed", error=str(e))
            raise
