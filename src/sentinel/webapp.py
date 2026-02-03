from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from sentinel.ui.presets import PRESETS
from sentinel.ui.schemas import ScanRequest
from sentinel.ui.service import run_scan

BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
TEMPLATES_DIR = UI_DIR / "templates"
STATIC_DIR = UI_DIR / "static"

app = FastAPI(title="SENTINEL Web", version="1.0")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    # simple server-side injection of presets list
    preset_options = "\n".join(
        f'<option value="{p.key}">{p.label}</option>' for p in PRESETS.values()
    )
    html = html.replace("{{PRESET_OPTIONS}}", preset_options)
    return HTMLResponse(content=html)


@app.get("/api/presets")
def presets():
    return {
        "presets": [
            {
                "key": p.key,
                "label": p.label,
                "timeframe": p.timeframe,
                "bars": p.bars,
                "refresh_seconds": p.refresh_seconds,
                "max_pairs": p.max_pairs,
            }
            for p in PRESETS.values()
        ]
    }


@app.post("/api/scan")
def api_scan(payload: dict):
    # Safe parsing with defaults
    req = ScanRequest(**payload)
    res = run_scan(req)
    return {
        "exchange": res.exchange,
        "timeframe": res.timeframe,
        "bars": res.bars,
        "refresh_seconds": res.refresh_seconds,
        "rows": [r.__dict__ for r in res.rows],
        "briefing": res.briefing,
    }
