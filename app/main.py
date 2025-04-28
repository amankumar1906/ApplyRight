from fastapi import FastAPI
from app.api import submit  # We'll add status, result, feedback later

app = FastAPI()

app.include_router(submit.router, prefix="/api")
