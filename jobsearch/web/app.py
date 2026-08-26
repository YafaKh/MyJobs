"""FastAPI dashboard: two tabs (saved sources / open web), star/correct/hide,
and a source health page. Run with: python -m jobsearch.cli serve
"""

import sqlite3
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from jobsearch.config import load_config
from jobsearch.db import connect
from jobsearch.web import queries

TEMPLATES_DIR = Path(__file__).parent / "templates"
VALID_SOURCE_KINDS = ("saved", "openweb")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app = FastAPI(title="Job Search")
config = load_config()


def get_conn() -> sqlite3.Connection:
    return connect(config["storage"]["db_path"])


@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse(url="/jobs/saved")


@app.get("/jobs/{source_kind}", response_class=HTMLResponse)
def jobs_page(request: Request, source_kind: str, q: str = "") -> HTMLResponse:
    if source_kind not in VALID_SOURCE_KINDS:
        raise HTTPException(status_code=404)
    conn = get_conn()
    try:
        jobs = queries.list_jobs(conn, source_kind, q)
    finally:
        conn.close()
    return templates.TemplateResponse(
        request, "jobs_page.html", {"jobs": jobs, "source_kind": source_kind, "active_tab": source_kind, "q": q}
    )


@app.get("/jobs/{source_kind}/list", response_class=HTMLResponse)
def jobs_list(request: Request, source_kind: str, q: str = "") -> HTMLResponse:
    if source_kind not in VALID_SOURCE_KINDS:
        raise HTTPException(status_code=404)
    conn = get_conn()
    try:
        jobs = queries.list_jobs(conn, source_kind, q)
    finally:
        conn.close()
    return templates.TemplateResponse(request, "_job_list.html", {"jobs": jobs})


@app.post("/jobs/{job_id}/star", response_class=HTMLResponse)
def star_job(request: Request, job_id: int) -> HTMLResponse:
    conn = get_conn()
    try:
        queries.toggle_star(conn, job_id)
        job = queries.get_job(conn, job_id)
    finally:
        conn.close()
    if job is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "_job_row.html", {"job": job})


@app.post("/jobs/{job_id}/hide", response_class=HTMLResponse)
def hide_job(job_id: int) -> HTMLResponse:
    conn = get_conn()
    try:
        queries.set_hidden(conn, job_id, True)
    finally:
        conn.close()
    return HTMLResponse("")


@app.post("/jobs/{job_id}/correct", response_class=HTMLResponse)
def correct_job(request: Request, job_id: int, field_name: str = Form(...), value: str = Form(...)) -> HTMLResponse:
    conn = get_conn()
    try:
        try:
            queries.apply_correction(conn, job_id, field_name, value)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        job = queries.get_job(conn, job_id)
    finally:
        conn.close()
    if job is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "_job_row.html", {"job": job})


@app.get("/sources", response_class=HTMLResponse)
def sources_page(request: Request) -> HTMLResponse:
    conn = get_conn()
    try:
        sources = queries.list_sources(conn)
    finally:
        conn.close()
    return templates.TemplateResponse(request, "sources.html", {"sources": sources, "active_tab": "sources"})
