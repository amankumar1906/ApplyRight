from fastapi import APIRouter, UploadFile, File, Form
from uuid import uuid4
import shutil
import os
import asyncio

from app.core.kafka_producer import send_resume_job

router = APIRouter()

UPLOAD_DIR = "uploads"

@router.post("/submit")
async def submit_resume(
    resume_file: UploadFile = File(...),
    job_description_text: str = Form(...)
):
    task_id = str(uuid4())

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    resume_path = os.path.join(UPLOAD_DIR, f"{task_id}_resume.pdf")
    jd_path = os.path.join(UPLOAD_DIR, f"{task_id}_jd.txt")

    with open(resume_path, "wb") as f:
        shutil.copyfileobj(resume_file.file, f)

    with open(jd_path, "w", encoding="utf-8") as f:
        f.write(job_description_text)

    job_payload = {
        "task_id": task_id,
        "resume_path": resume_path,
        "jd_path": jd_path,
        "status": "queued"
    }
    await send_resume_job(job_payload)

    return {"task_id": task_id, "message": "Resume tailoring job submitted successfully."}
