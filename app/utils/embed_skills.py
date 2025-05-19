# app/utils/embed_skills.py

from sentence_transformers import SentenceTransformer
from typing import List

# Load upgraded embedding model (768-dim)
model = SentenceTransformer("mixedbread-ai/mxbai-embed-large-v1")

def embed_skills(skills: List[dict], job_title: str = "") -> List[float]:
    """
    Convert a structured skill list (with evidence + weights) and optional job title
    into a 768-dim semantic vector.
    """
    if not skills:
        return [0.0] * 768  # return zero vector if no skills

    enriched_lines = []
    for skill in skills:
        name = skill.get("skill", "")
        evidence = skill.get("evidence", "")
        weight = skill.get("weight", 0)
        enriched_line = f"[{weight}/10] {name}: {evidence}"
        enriched_lines.append(enriched_line)

    # Prefix with job title for context
    enriched_text = f"Job Title: {job_title}\n" + "\n".join(enriched_lines)

    # Generate embedding
    embedding = model.encode(enriched_text, normalize_embeddings=True)
    return embedding.tolist()
