from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import init_db, engine
from app.db.seed import seed_incidents
from sqlmodel import Session
from app.api import triage, incidents, reports, taxonomy, seed

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage.router,    prefix=settings.API_PREFIX, tags=["triage"])
app.include_router(incidents.router, prefix=settings.API_PREFIX, tags=["incidents"])
app.include_router(reports.router,   prefix=settings.API_PREFIX, tags=["reports"])
app.include_router(taxonomy.router,  prefix=settings.API_PREFIX, tags=["taxonomy"])
app.include_router(seed.router,      prefix=settings.API_PREFIX, tags=["seed"])


@app.on_event("startup")
def on_startup():
    init_db()
    with Session(engine) as session:
        seeded = seed_incidents(session)
        if seeded:
            print(f"[startup] Seeded {seeded} incidents")

        # Pre-compute embeddings for all incidents
        try:
            from app.services.retrieval import precompute_embeddings
            embedded = precompute_embeddings(session)
            if embedded:
                print(f"[startup] Computed embeddings for {embedded} incidents")
        except Exception as e:
            print(f"[startup] Embedding pre-computation skipped: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}
