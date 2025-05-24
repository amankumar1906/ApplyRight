from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ Replace this with your frontend's origin
origins = [
    "http://127.0.0.1:8081",
    "http://localhost:8081"
]

# ✅ Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # allows your frontend
    allow_credentials=True,
    allow_methods=["*"],          # allows all HTTP methods
    allow_headers=["*"],          # allows all headers
)

# Now include your routers
from app.api import submit
from app.api.feedback import router as feedback_router
from app.api.status import router as status_router
from app.api.result import router as result_router

app.include_router(submit.router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(status_router, prefix="/api")
app.include_router(result_router, prefix="/api")
