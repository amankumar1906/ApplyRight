import numpy as np
from app.core.config import Config

supabase = Config.SUPABASE

async def find_most_similar_resume(jd_embedding: list[float], top_k=3):
    if not jd_embedding:
        raise ValueError("Embedding must be provided for similarity search.")

    # Create SQL query with casting to match expected column types
    raw_query = f"""
        SELECT task_id, resume_url, tailored_resume_text, job_title,
               embedding <#> ARRAY{jd_embedding}::vector AS similarity
        FROM resume_jobs
        WHERE embedding IS NOT NULL
        ORDER BY similarity ASC
        LIMIT {top_k}
    """

    # Wrap with a subquery and alias each column's type for pg compatibility
    wrapped_query = f"""
        SELECT * FROM (
            {raw_query}
        ) AS t(
            task_id UUID,
            resume_url TEXT,
            tailored_resume_text TEXT,
            job_title TEXT,
            similarity DOUBLE PRECISION
        )
    """

    response = supabase.rpc("exec_sql", {"sql": wrapped_query}).execute()
    if response.error:
        raise RuntimeError(f"Vector search error: {response.error.message}")

    return response.data
