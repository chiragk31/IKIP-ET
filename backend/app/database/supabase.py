"""
Supabase Client Wrapper

Repository-level abstraction over the Supabase Python SDK.
All Supabase interactions must go through this client.

Responsibilities:
- Authentication operations
- File storage (upload, download, delete, signed URLs)
- Database operations (metadata CRUD)

Never call the Supabase SDK directly from services.
Always use this wrapper or the specific repositories built on top of it.
"""

from typing import Optional, Any, Dict
import structlog
from supabase import create_client, Client

logger = structlog.get_logger(__name__)


class SupabaseClient:
    """
    Supabase client wrapper.

    Provides a clean interface to Supabase storage and database operations.
    All methods are synchronous to match the Supabase Python SDK.
    For async support, use run_in_executor where needed.
    """

    def __init__(self, url: str, service_role_key: str) -> None:
        """
        Initialize the Supabase client.

        Args:
            url: Supabase project URL
            service_role_key: Service role key (has full access, use carefully)
        """
        self.url = url
        self._client: Optional[Client] = None
        self._service_role_key = service_role_key
        logger.info("supabase_client_init", url=url)

    def _get_client(self) -> Client:
        """
        Get or create Supabase client (lazy initialization).

        Returns:
            Client: Supabase client instance
        """
        if self._client is None:
            self._client = create_client(self.url, self._service_role_key)
        return self._client

    @property
    def client(self) -> Client:
        """Supabase client property."""
        return self._get_client()

    @property
    def storage(self):
        """Supabase storage interface."""
        return self._get_client().storage

    @property
    def db(self):
        """Supabase database interface."""
        return self._get_client().table

    def health_check(self) -> Dict[str, Any]:
        """
        Verify Supabase connection is functional.

        Uses the Supabase auth endpoint as a lightweight ping so the check
        works even before database tables are created.

        Returns:
            Dict with status and details

        Raises:
            Exception: If connection fails (network, wrong URL, invalid key)
        """
        try:
            client = self._get_client()

            # Try a lightweight table query first
            try:
                client.table("documents").select("id").limit(1).execute()
                return {"status": "up", "url": self.url}
            except Exception as e:
                error_str = str(e)
                error_code = ""

                # Extract PGRST error code if present
                if isinstance(e, dict):
                    error_code = e.get("code", "")
                elif hasattr(e, "args") and e.args:
                    # Check raw error dict inside the exception args
                    for arg in e.args:
                        if isinstance(arg, dict):
                            error_code = arg.get("code", "")
                            break

                # Also check the string representation
                if "PGRST205" in error_str or "Could not find the table" in error_str:
                    # Table doesn't exist yet — connection is fine, just no schema
                    logger.info(
                        "supabase_tables_not_created",
                        note="Database is connected but tables are not yet created. Run the SQL migration.",
                    )
                    return {
                        "status": "up",
                        "url": self.url,
                        "note": "Connected — tables not yet created. Run docs/migrations/001_initial_schema.sql in Supabase SQL Editor.",
                    }
                raise

        except Exception as e:
            logger.error("supabase_health_check_failed", error=str(e))
            raise
