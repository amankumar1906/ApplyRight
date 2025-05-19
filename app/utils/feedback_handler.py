from app.core.config import Config
from app.utils.embed_skills import embed_skills

supabase = Config.SUPABASE

async def handle_resume_feedback(task_id: str, rating: int):
    if rating < 5:
        supabase.table("resume_jobs").update({"rating": rating}).eq("task_id", task_id).execute()
        print(f"[⭐] Task {task_id} rated {rating} — skipping embedding.")
        return

    print(f"[🌟] Task {task_id} rated 5★ — embedding resume.")

    # Fetch skills
    result = supabase.table("resume_jobs").select("skills").eq("task_id", task_id).execute()
    if not result.data or not result.data[0].get("skills"):
        print(f"[⚠️] No skills found for {task_id}. Skipping embedding.")
        return

    skills = result.data[0]["skills"]
    embedding = embed_skills(skills)

    # Update with embedding
    supabase.table("resume_jobs").update({
        "embedding": embedding,
        "rating": rating
    }).eq("task_id", task_id).execute()

    print(f"[✅] Embedding stored for {task_id}")
