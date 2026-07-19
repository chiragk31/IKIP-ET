"""
Neo4j Client Wrapper

Repository-level abstraction over the Neo4j Python driver.
All Neo4j interactions must go through this client or repositories built on it.

Responsibilities:
- Graph database connection management
- Session and transaction management
- Health verification

Critical Rules:
- The LLM NEVER generates Cypher queries.
- Only GraphBuilder may write to Neo4j.
- This client only provides the connection infrastructure.
"""

from typing import Optional, Any, Dict, List
import structlog
from neo4j import GraphDatabase, Driver, Session

logger = structlog.get_logger(__name__)


class Neo4jClient:
    """
    Neo4j driver wrapper.

    Manages the connection to Neo4j Aura and provides
    session/transaction helpers for repositories.
    """

    def __init__(self, uri: str, username: str, password: str) -> None:
        """
        Initialize the Neo4j client.

        Args:
            uri: Neo4j connection URI (e.g., neo4j+s://xxx.databases.neo4j.io)
            username: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.username = username
        self._password = password
        self._driver: Optional[Driver] = None
        logger.info("neo4j_client_init", uri=uri, username=username)

    def _get_driver(self) -> Driver:
        """
        Get or create Neo4j driver (lazy initialization).

        Returns:
            Driver: Neo4j driver instance
        """
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self._password),
            )
        return self._driver

    def get_session(self) -> Session:
        """
        Get a new Neo4j session.

        Returns:
            Session: Neo4j session for executing queries
        """
        return self._get_driver().session()

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        with self.get_session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def health_check(self) -> Dict[str, Any]:
        """
        Verify Neo4j connection is functional.

        Returns:
            Dict with status and details

        Raises:
            Exception: If connection fails
        """
        try:
            driver = self._get_driver()
            driver.verify_connectivity()
            return {"status": "up", "uri": self.uri}
        except Exception as e:
            logger.error("neo4j_health_check_failed", error=str(e))
            raise

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("neo4j_client_closed")
