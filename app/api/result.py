from fastapi import APIRouter, Query, HTTPException
from app.core.config import Config

router = APIRouter()
supabase = Config.SUPABASE

@router.get("/result")
async def get_tailored_resume_url(task_id: str = Query(...)):
    try:
        result = supabase.table("resume_jobs") \
            .select("tailored_resume_url") \
            .eq("task_id", task_id) \
            .limit(1) \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Task ID not found")

        tailored_url = result.data[0].get("tailored_resume_url")
        if not tailored_url:
            raise HTTPException(status_code=404, detail="Tailored resume not available yet")

        return {"tailored_resume_url": tailored_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching result: {str(e)}")
