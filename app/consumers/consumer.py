import asyncio
import json

from aiokafka import AIOKafkaConsumer
from app.core.config import Config
from app.utils.parser import parse_resume_pdf, parse_job_description
from app.utils.jd_metadata_extraction import extract_jd_metadata_llm

# ------------------ Kafka Batch Consumer ------------------ #
async def consume_resume_jobs():
    consumer = AIOKafkaConsumer(
        Config.REDPANDA_TOPIC_NAME,
        bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True
    )

    await consumer.start()
    print("[✅] Kafka Batch Consumer Started... Listening for jobs")

    try:
        while True:
            # pull up to 10 messages, or wait 500ms
            messages = await consumer.getmany(timeout_ms=500, max_records=10)

            for tp, batch in messages.items():
                print(f"[📦] Processing batch of {len(batch)} jobs...")

                tasks = []
                for msg in batch:
                    job_data = msg.value
                    print(f"[📥] New job: {job_data}")

                    task_id   = job_data.get("task_id")
                    resume_path = job_data.get("resume_path")
                    jd_path   = job_data.get("jd_path")

                    if not (task_id and resume_path and jd_path):
                        print(f"[⚠️] Invalid payload, skipping: {job_data}")
                        continue

                    # schedule the processing coroutine
                    tasks.append(process_resume_job(task_id, resume_path, jd_path))

                if tasks:
                    # run them concurrently
                    await asyncio.gather(*tasks)

    except Exception as e:
        print(f"[❌] Consumer error: {e}")
    finally:
        await consumer.stop()
        print("[🛑] Kafka Consumer Stopped.")

# --------------- Per-Job Processor ---------------- #

async def process_resume_job(task_id: str, resume_path: str, jd_path: str):
    print(f"[🛠️] Processing Task ID: {task_id}")

    # 1) extract raw text
    resume_text = parse_resume_pdf(resume_path)
    jd_text     = parse_job_description(jd_path)

    # 2) ask LLM to pull out skills + weights + evidence + title
    jd_metadata = await extract_jd_metadata_llm(jd_text)
    print(f"[📑] Extracted JD Metadata for {task_id}:")
    print(jd_metadata)

    # TODO:
    # 3) embed jd_metadata → store/query in vector DB
    # 4) fetch top-3 resumes → tailor final resume via LangChain agent
    # 5) save tailored resume + update status

    await asyncio.sleep(1)  # placeholder
    print(f"[✅] Finished metadata extraction for Task ID: {task_id}")
