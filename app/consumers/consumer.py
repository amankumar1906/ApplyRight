import asyncio
import json
import logging
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
from aiokafka import AIOKafkaConsumer
from app.core.config import Config
from app.utils.parser import parse_resume_pdf, parse_job_description
from app.utils.jd_metadata_extraction import extract_jd_metadata_llm
from app.utils.resume_generator import generate_tailored_resume
from app.utils.upload_to_supabase import upload_file_to_supabase
from app.utils.embed_skills import embed_skills
from app.utils.vector_search import find_most_similar_resume
import mimetypes
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

supabase = Config.SUPABASE

# ------------------- Update Status -------------------------#
async def update_job_status(task_id: str, status: str):
    try:
        supabase.table("resume_jobs").update({"status": status}).eq("task_id", task_id).execute()
        logger.info(f"[📌] Status updated to '{status}' for task {task_id}")
    except Exception as e:
        logger.warning(f"[⚠️] Failed to update status for {task_id}: {e}")


# ------------------ Kafka Batch Consumer ------------------ #
async def consume_resume_jobs():
    """
    Consume resume processing jobs from Kafka and process them in batches.
    """
    consumer = AIOKafkaConsumer(
        Config.REDPANDA_TOPIC_NAME,
        bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True
    )

    try:
        await consumer.start()
        logger.info("[✅] Kafka Batch Consumer Started...")

        while True:
            messages = await consumer.getmany(timeout_ms=500, max_records=10)

            for tp, batch in messages.items():
                logger.info(f"[📦] Processing {len(batch)} job(s)...")

                tasks = []
                for msg in batch:
                    job_data = msg.value
                    logger.info(f"[📥] New job received: {job_data.get('task_id')}")

                    task_id = job_data.get("task_id")
                    resume_path = job_data.get("resume_path")
                    jd_path = job_data.get("jd_path")

                    if not (task_id and resume_path and jd_path):
                        logger.warning(f"[⚠️] Skipping invalid payload: {job_data}")
                        continue

                    tasks.append(process_resume_job(task_id, resume_path, jd_path))

                if tasks:
                    await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"[❌] Consumer error: {e}")
        raise
    finally:
        await consumer.stop()
        logger.info("[🛑] Kafka Consumer Stopped.")

# --------------- Per-Job Processor ---------------- #
async def process_resume_job(task_id: str, resume_path: str, jd_path: str):
    """
    Process a single resume job: parse, generate tailored resume, upload files, and store metadata.
    
    Args:
        task_id (str): Unique task identifier.
        resume_path (str): Path to the original resume PDF.
        jd_path (str): Path to the job description.
    """
    logger.info(f"[🛠️] Processing Task ID: {task_id}")

    try:
        # 1) Extract text
        resume_text = parse_resume_pdf(resume_path)
        jd_text = parse_job_description(jd_path)
        if not resume_text or not jd_text:
            raise ValueError("Failed to parse resume or job description")

        # 2) Extract JD metadata
        jd_metadata = await extract_jd_metadata_llm(jd_text)
        logger.info(f"[📑] Extracted JD Metadata for {task_id}")

        # 3) Embed metadata for vector similarity
        embedding = embed_skills(jd_metadata["skills"], jd_metadata.get("job_title", ""))
        embedding = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding

        # 4) Query for most similar resumes
        top_matches = await find_most_similar_resume(embedding)
        reference_texts = "\n\n---\n\n".join(
            m["tailored_resume_text"] for m in top_matches if m.get("tailored_resume_text")
        )
        logger.info(f"[🔍] Retrieved reference resumes for {task_id}")

        # 5) Generate tailored resume
        tailored_resume_text, tailored_resume_docx = await generate_tailored_resume(
            resume_text=resume_text,
            jd_metadata=jd_metadata,
            reference_resumes=reference_texts
        )
        logger.info(f"[✍️] Tailored resume generated for {task_id}")

        skills = jd_metadata.get("skills", [])

        # 6) Upload files and store metadata (without transaction)
        try:
            # Upload original resume PDF
            resume_url = await upload_file_to_supabase(
                bucket="resume-files",
                file_path=resume_path,
                destination_path=f"{task_id}/original_resume.pdf"
            )

            # Upload tailored resume Word doc
            tailored_resume_url = await upload_file_to_supabase(
                bucket="resume-files",
                file_path=tailored_resume_docx,
                destination_path=f"{task_id}/tailored_resume.docx"
            )

            # Validate required fields
            if not all([task_id, resume_url, tailored_resume_url, tailored_resume_text]):
                raise ValueError(f"Missing required fields for task {task_id}")

            # Check for existing task_id and upsert data
            existing = supabase.table("resume_jobs").select("task_id").eq("task_id", task_id).execute()
            
            data_to_store = {
                "task_id": task_id,
                "resume_url": resume_url,
                "tailored_resume_url": tailored_resume_url,
                "jd_text": jd_text,
                "tailored_resume_text": tailored_resume_text,
                "skills": skills,
                "job_title": jd_metadata.get("job_title", ""),
                "embedding": embedding,
                "rating": None
            }
            
            if existing.data:
                logger.info(f"[⚠️] Task ID {task_id} already exists, updating instead")
                supabase.table("resume_jobs").update(data_to_store).eq("task_id", task_id).execute()
            else:
                supabase.table("resume_jobs").insert(data_to_store).execute()

            logger.info(f"[✅] Task {task_id} successfully stored in Supabase")
            await update_job_status(task_id, "completed")


        except Exception as db_error:
            logger.error(f"[❌] Database operation failed for task {task_id}: {db_error}")
            # If database operation fails, you might want to clean up uploaded files
            # or implement a retry mechanism
            raise

    except Exception as e:
        logger.error(f"[❌] Failed to process task {task_id}: {e}")
        raise