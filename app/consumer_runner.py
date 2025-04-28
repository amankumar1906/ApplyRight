import asyncio
from app.consumers.consumer import consume_resume_jobs

if __name__ == "__main__":
    asyncio.run(consume_resume_jobs())
