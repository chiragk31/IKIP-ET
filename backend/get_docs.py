from app.core.config import settings
from app.database.supabase import SupabaseClient
import asyncio

async def get_doc():
    supabase = SupabaseClient(url=settings.SUPABASE_URL, service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY)
    resp = supabase.client.table('documents').select('id, status').execute()
    for row in resp.data:
        print(f"{row['id']} - {row['status']}")

asyncio.run(get_doc())
