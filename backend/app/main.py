from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, documents, paystub_generate, paystubs, users
from app.core.config import settings

app = FastAPI(title=settings.project_name)

allowed_origins = [origin.strip() for origin in settings.allow_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "product": settings.project_name,
        "employer": settings.employer_legal_name,
        "time_zone": settings.time_zone,
    }


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(paystubs.router, prefix="/api/paystubs", tags=["paystubs"])
app.include_router(
    paystub_generate.router, prefix="/api/v1/paystubs", tags=["paystub-generator"]
)
