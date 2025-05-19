from fastapi import FastAPI
from app.api import submit
from app.api.feedback import router as feedback_router 

app = FastAPI()

app.include_router(submit.router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
