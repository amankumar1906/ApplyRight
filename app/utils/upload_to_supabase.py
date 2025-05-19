from app.core.config import Config
import mimetypes
import os

supabase = Config.SUPABASE

async def upload_file_to_supabase(bucket: str, file_path: str, destination_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/pdf" 

    with open(file_path, "rb") as f:
        file_data = f.read()

    supabase.storage.from_(bucket).upload(
        destination_path,
        file_data,
        {
            "content-type": mime_type, 
            "cacheControl": "3600",
            "upsert": "true"
        }
    )

    public_url = supabase.storage.from_(bucket).get_public_url(destination_path)
    return public_url
