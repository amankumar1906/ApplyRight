from fastapi import APIRouter, Query, HTTPException
from app.core.config import Config

router = APIRouter()
supabase = Config.SUPABASE

@router.get("/checkStatus")
async def check_status(task_id: str = Query(...)):
    try:
        result = supabase.table("resume_jobs").select("status").eq("task_id", task_id).limit(1).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Task ID not found")

        status = result.data[0]["status"]
        return {"completed": status == "completed"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")
