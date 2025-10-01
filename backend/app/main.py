from fastapi import FastAPI
from app.api.routes import events
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Add a simple health check endpoint for CORS testing
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running and CORS is configured"}

app.include_router(events.router, prefix="/api")