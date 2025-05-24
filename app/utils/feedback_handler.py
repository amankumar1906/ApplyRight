from app.core.config import Config

supabase = Config.SUPABASE

async def handle_resume_feedback(task_id: str, rating: int):
    supabase.table("resume_jobs").update({"rating": rating}).eq("task_id", task_id).execute()
    print(f"[⭐] Task {task_id} rated {rating} — rating updated.")
