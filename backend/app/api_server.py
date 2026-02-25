"""
Career26 REST API for the Electron/React desktop app.
Run with: uvicorn app.api_server:app --host 127.0.0.1 --port 8765
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# Project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

app = FastAPI(title="Career26 API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_API_KEYS = ("SERPAPI_KEY", "OPENAI_API_KEY", "ANYMAIL_API_KEY", "HUNTER_API_KEY")
_executor = ThreadPoolExecutor(max_workers=2)


# --- Request/Response models ---
class FindPeopleAtCompaniesRequest(BaseModel):
    companies: list[str]
    job_titles: list[str]
    max_per_company: int = 5


class FindEmailRequest(BaseModel):
    full_name: str
    company_or_domain: str
    resolve_domain: bool = True


class SearchPeopleRequest(BaseModel):
    query: str
    use_llm: bool = True


class SettingsGetResponse(BaseModel):
    keys: dict[str, bool]  # key name -> is set (masked)


class SettingsSaveRequest(BaseModel):
    keys: dict[str, str]  # key name -> value (empty = don't change)


# --- Endpoints ---
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Career26"}


@app.post("/api/load-file")
async def load_file(file: UploadFile = File(...)):
    """Upload CSV, PDF, or Excel; returns rows, columns, and extracted companies."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".pdf", ".xlsx", ".xls"):
        raise HTTPException(400, "Unsupported format. Use .csv, .pdf, or .xlsx")
    contents = await file.read()
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        try:
            from app.services import load_file_any, extract_companies_from_rows
            rows, cols, err = load_file_any(tmp_path)
            if err:
                return {"error": err, "rows": [], "columns": [], "companies": []}
            companies = extract_companies_from_rows(rows)
            return {"rows": rows, "columns": cols, "companies": companies, "error": None}
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/find-people-at-companies")
async def find_people_at_companies(body: FindPeopleAtCompaniesRequest):
    """Find people at given companies with given job titles."""
    def run():
        from app.services import find_people_at_companies as svc_find
        return svc_find(
            body.companies[:30],
            body.job_titles[:3] or ["Director", "Partner"],
            max_per_company=body.max_per_company,
            find_emails=True,
        )
    loop = __import__("asyncio").get_event_loop()
    results = await loop.run_in_executor(_executor, run)
    return {"results": results}


@app.post("/api/find-email")
async def find_email(body: FindEmailRequest):
    """Find email with step-by-step log and optional domain suggestions."""
    def run():
        from app.services import find_email_with_log
        return find_email_with_log(
            body.full_name,
            body.company_or_domain,
            resolve_domain=body.resolve_domain,
        )
    loop = __import__("asyncio").get_event_loop()
    email, confidence, log_lines, suggestions = await loop.run_in_executor(_executor, run)
    return {
        "email": email,
        "confidence": confidence,
        "log": log_lines,
        "suggestions": [{"display": s[0], "domain": s[1]} for s in suggestions],
    }


@app.post("/api/search-people")
async def search_people(body: SearchPeopleRequest):
    """Natural-language people search, optionally LLM-enhanced."""
    def run():
        from app.services import llm_enhance_search_query, people_search
        query = llm_enhance_search_query(body.query) if body.use_llm else body.query
        results = people_search(query, max_results=15, find_emails=True)
        return query, results
    loop = __import__("asyncio").get_event_loop()
    enhanced_query, results = await loop.run_in_executor(_executor, run)
    return {
        "results": results,
        "enhanced_query": enhanced_query if body.use_llm else None,
    }


@app.post("/api/export-csv")
async def export_csv(body: dict):
    """Export rows to CSV. Body: { rows, columns }. Returns CSV file."""
    rows = body.get("rows") or []
    columns = body.get("columns") or (list(rows[0].keys()) if rows else [])
    if not rows:
        raise HTTPException(400, "No rows to export")
    from app.services import export_results_csv
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        err = export_results_csv(rows, tmp_path, columns)
        if err:
            raise HTTPException(500, err)
        with open(tmp_path, "rb") as f:
            data = f.read()
        return Response(content=data, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=export.csv"})
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.get("/api/settings/keys", response_model=SettingsGetResponse)
def get_settings():
    """Return which API keys are set (masked)."""
    return {"keys": {k: bool(os.environ.get(k)) for k in _API_KEYS}}


@app.post("/api/settings/save")
def save_settings(body: SettingsSaveRequest):
    """Save API keys to .env. Only non-empty values are written."""
    from app.services import save_env_keys
    for k, v in body.keys.items():
        if v and k in _API_KEYS:
            os.environ[k] = v
    save_env_keys(_ROOT / ".env", _API_KEYS, lambda key: body.keys.get(key, ""))
    return {"status": "saved"}


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
