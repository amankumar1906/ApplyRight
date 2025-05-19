import os
from dotenv import load_dotenv
from supabase import create_client, Client

class Config:
    load_dotenv()

    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    REDPANDA_TOPIC_NAME = os.getenv("REDPANDA_TOPIC_NAME")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")
    OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    SUPABASE: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)
