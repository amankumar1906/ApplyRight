from fastapi import FastAPI
from app.api import submit
from app.api.feedback import router as feedback_router
from app.api.status import router as status_router
from app.api.result import router as result_router


app = FastAPI()

app.include_router(submit.router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(status_router, prefix="/api")
app.include_router(result_router, prefix="/api")
