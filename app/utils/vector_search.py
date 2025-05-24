import numpy as np
from app.core.config import Config

supabase = Config.SUPABASE

async def find_most_similar_resume(jd_embedding: list[float], top_k=3):
    if not jd_embedding:
        raise ValueError("Embedding must be provided for similarity search.")

    raw_query = f"""
        SELECT task_id, resume_url, tailored_resume_text, job_title,
               embedding <#> ARRAY{jd_embedding}::vector AS similarity
        FROM resume_jobs
        WHERE embedding IS NOT NULL AND rating >= 4
        ORDER BY similarity ASC
        LIMIT {top_k}
    """

    try:
        response = supabase.rpc("exec_sql", {"sql": raw_query}).execute()
        if hasattr(response, 'data') and response.data:
            return response.data
        else:
            print(f"[⚠️] No matching resumes found for embedding")
            return []
    except Exception as e:
        raise RuntimeError(f"Vector search failed: {str(e)}")
