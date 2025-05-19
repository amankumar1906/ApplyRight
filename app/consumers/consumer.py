# app/consumers/resume_consumer.py

import asyncio
import json

from aiokafka import AIOKafkaConsumer
from app.core.config import Config
from app.utils.parser import parse_resume_pdf, parse_job_description
from app.utils.jd_metadata_extraction import extract_jd_metadata_llm
from app.utils.resume_generator import generate_tailored_resume
from app.utils.upload_to_supabase import upload_file_to_supabase
from app.utils.embed_skills import embed_skills
from app.utils.vector_search import find_most_similar_resume

supabase = Config.SUPABASE

# ------------------ Kafka Batch Consumer ------------------ #
async def consume_resume_jobs():
    consumer = AIOKafkaConsumer(
        Config.REDPANDA_TOPIC_NAME,
        bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True
    )

    await consumer.start()
    print("[✅] Kafka Batch Consumer Started...")

    try:
        while True:
            messages = await consumer.getmany(timeout_ms=500, max_records=10)

            for tp, batch in messages.items():
                print(f"[📦] Processing {len(batch)} job(s)...")

                tasks = []
                for msg in batch:
                    job_data = msg.value
                    print(f"[📥] New job received: {job_data.get('task_id')}")

                    task_id = job_data.get("task_id")
                    resume_path = job_data.get("resume_path")
                    jd_path = job_data.get("jd_path")

                    if not (task_id and resume_path and jd_path):
                        print(f"[⚠️] Skipping invalid payload: {job_data}")
                        continue

                    tasks.append(process_resume_job(task_id, resume_path, jd_path))

                if tasks:
                    await asyncio.gather(*tasks)

    except Exception as e:
        print(f"[❌] Consumer error: {e}")
    finally:
        await consumer.stop()
        print("[🛑] Kafka Consumer Stopped.")

# --------------- Per-Job Processor ---------------- #
async def process_resume_job(task_id: str, resume_path: str, jd_path: str):
    print(f"[🛠️] Processing Task ID: {task_id}")

    # 1) Extract text
    resume_text = parse_resume_pdf(resume_path)
    jd_text = parse_job_description(jd_path)

    # 2) Extract JD metadata
    jd_metadata = await extract_jd_metadata_llm(jd_text)
    print(f"[📑] Extracted JD Metadata for {task_id}")

    # 3) Embed metadata for vector similarity
    embedding = embed_skills(jd_metadata["skills"], jd_metadata.get("job_title", ""))

    # 4) Query for most similar resumes
    top_matches = await find_most_similar_resume(embedding)
    reference_texts = "\n\n---\n\n".join(
        m["tailored_resume_text"] for m in top_matches if m.get("tailored_resume_text")
    )

    # 5) Generate tailored resume with context
    tailored_resume_text = await generate_tailored_resume(
        resume_text=resume_text,
        jd_metadata=jd_metadata,
        reference_resumes=reference_texts  # <-- pass in top matching resume text
    )
    print(f"[✍️] Tailored resume generated for {task_id}")

    skills = jd_metadata.get("skills", [])

    # 6) Upload original resume PDF
    resume_url = await upload_file_to_supabase(
        bucket="resume-files",
        file_path=resume_path,
        destination_path=f"{task_id}/original_resume.pdf"
    )

    # 7) Store all in Supabase
    supabase.table("resume_jobs").insert({
        "task_id": task_id,
        "resume_url": resume_url,
        "jd_text": jd_text,
        "tailored_resume_text": tailored_resume_text,
        "skills": skills,
        "job_title": jd_metadata.get("job_title", ""),
        "embedding": embedding,
        "rating": None
    }).execute()

    print(f"[✅] Task {task_id} successfully stored in Supabase")