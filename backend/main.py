import os
import shutil
import traceback
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from config import WORK_DIR_ROOT, MAX_UPLOAD_MB
from pipeline import run_analysis

app = FastAPI(title="AutoGen Data Analyst API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(WORK_DIR_ROOT, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(question: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    upload_dir = os.path.join(WORK_DIR_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    csv_path = os.path.join(upload_dir, f"{uuid.uuid4().hex[:8]}_{file.filename}")

    with open(csv_path, "wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        os.remove(csv_path)
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_UPLOAD_MB}MB allowed.")

    try:
        result = run_analysis(csv_path=csv_path, question=question)

        print("=" * 80)
        print(result["transcript"])
        print("=" * 80)
    except Exception as exc:
        print("----- /analyze failed, full traceback below -----")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    return {
        "run_id": result["run_id"],
        "summary": result["summary"],
        "approved": result["approved"],
        "review_feedback": result["review_feedback"],
        "chart_url": f"/chart/{result['run_id']}" if result["chart_path"] else None,
    }


@app.get("/chart/{run_id}")
def get_chart(run_id: str):
    chart_path = os.path.join(WORK_DIR_ROOT, run_id, "chart.png")
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="Chart not found.")
    return FileResponse(chart_path, media_type="image/png")
