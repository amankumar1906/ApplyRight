from aiokafka import AIOKafkaProducer
import json
import asyncio

from app.core.config import Config

async def send_resume_job(data: dict):
    """
    Publish a resume tailoring job message to Kafka.
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    await producer.start()
    try:
        await producer.send_and_wait(Config.REDPANDA_TOPIC_NAME, data)
        print(f"[📤] Job published to {Config.REDPANDA_TOPIC_NAME}: {data['task_id']}")
    finally:
        await producer.stop()
