import logging
import mimetypes
import os
from io import BytesIO
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

supabase = Config.SUPABASE

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def upload_file_to_supabase(bucket: str, file_path: str | BytesIO, destination_path: str) -> str:
    """
    Upload a file to Supabase storage and return its public URL.

    Args:
        bucket (str): Supabase storage bucket name.
        file_path (str | BytesIO): Path to file or BytesIO buffer.
        destination_path (str): Destination path in the bucket.

    Returns:
        str: Public URL of the uploaded file.

    Raises:
        ValueError: If input parameters are invalid or file is inaccessible.
        Exception: If upload or URL retrieval fails after retries.
    """
    # Validate inputs
    if not bucket or not destination_path:
        logger.error("Bucket or destination path is empty")
        raise ValueError("Bucket or destination path is empty")

    try:
        # Determine MIME type and read file data
        if isinstance(file_path, BytesIO):
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            file_path.seek(0)
            file_data = file_path.read()
            if not file_data:
                logger.error("BytesIO buffer is empty")
                raise ValueError("BytesIO buffer is empty")
        else:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                raise ValueError(f"File does not exist: {file_path}")
            if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
                logger.error(f"File is not readable: {file_path}")
                raise ValueError(f"File is not readable: {file_path}")
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "application/pdf"
            with open(file_path, "rb") as f:
                file_data = f.read()

        # Upload to Supabase
        logger.info(f"Uploading file to Supabase bucket {bucket} at {destination_path}")
        supabase.storage.from_(bucket).upload(
            destination_path,
            file_data,
            {
                "content-type": mime_type,
                "cacheControl": "3600",
                "upsert": "true"
            }
        )

        # Retrieve public URL
        public_url = supabase.storage.from_(bucket).get_public_url(destination_path)
        if not public_url:
            logger.error(f"No public URL returned for {destination_path}")
            raise ValueError(f"No public URL returned for {destination_path}")
        
        logger.info(f"Successfully uploaded file to {destination_path}. Public URL: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Failed to upload file to Supabase bucket {bucket} at {destination_path}: {e}")
        raise