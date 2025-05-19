from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from app.utils.feedback_handler import handle_resume_feedback

router = APIRouter()

@router.post("/submit-feedback")
async def submit_feedback(
    task_id: str = Form(...),
    rating: int = Form(...)
):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")

    try:
        await handle_resume_feedback(task_id, rating)
        return {"message": "Feedback received and processed successfully."}
    except Exception as e:
        print(f"[❌] Error in feedback handler: {e}")
        raise HTTPException(status_code=500, detail="Failed to process feedback.")
