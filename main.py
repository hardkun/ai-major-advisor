"""AI 相关专业择校参考助手 API 入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db import check_db_status, init_db
from routers import (
    admissions,
    bulk_pipeline,
    collector_runs,
    collectors,
    data_sources,
    gap_diagnosis,
    file_links,
    import_batches,
    majors,
    raw_admission_records,
    raw_data_sources,
    recommend,
    reports,
    schools,
    search_tools,
    source_checks,
    source_candidates,
    source_diagnostics,
    verification,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动创建或迁移数据库表。"""
    init_db()
    yield


app = FastAPI(
    title="AI Major Advisor API",
    description="AI 相关专业择校参考助手 MVP",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schools.router)
app.include_router(search_tools.router)
app.include_router(majors.router)
app.include_router(admissions.router)
app.include_router(bulk_pipeline.router)
app.include_router(collectors.router)
app.include_router(collector_runs.router)
app.include_router(recommend.router)
app.include_router(reports.router)
app.include_router(data_sources.router)
app.include_router(gap_diagnosis.router)
app.include_router(file_links.router)
app.include_router(import_batches.router)
app.include_router(raw_data_sources.router)
app.include_router(raw_admission_records.router)
app.include_router(source_checks.router)
app.include_router(source_candidates.router)
app.include_router(source_diagnostics.router)
app.include_router(verification.router)

app.mount("/admin", StaticFiles(directory="admin", html=True), name="admin")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/db/status", tags=["system"])
def db_status() -> dict[str, str]:
    return check_db_status()
