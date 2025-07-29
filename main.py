from pathlib import Path
import shutil
import traceback
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import uvicorn
import os
import numpy as np
import requests
import warnings
import logging

# Suppress warnings (e.g., Pydantic V2)
warnings.filterwarnings("ignore", category=UserWarning)

# Clean up noisy loggers
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("pydantic").setLevel(logging.ERROR)

from app.controllers.notification_controller import check_and_send_scheduled_notifications
from app.routes import (
    password_reset_routes, users, plans, payments, resources, reports, notifications,
     authme, subscriptions, financialmetrics
)
from app.controllers.resource_controller import get_all_resources
from app.algorithm import truetypealgorithm
from app.algorithm.algoimplementation import total_score
from app.database.init_db import create_database_if_not_exists
from app.utils.scheduler import start

load_dotenv()

app = FastAPI(title="Plagiarism Detection API")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.on_event("startup")
def startup_event():
    create_database_if_not_exists()
    check_and_send_scheduled_notifications()
    start()
    print("✅ Server is ready.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users.router)
app.include_router(plans.router)
app.include_router(payments.router)
app.include_router(resources.router)
app.include_router(reports.router)
app.include_router(notifications.router)
app.include_router(authme.router)
app.include_router(financialmetrics.router)
app.include_router(subscriptions.router)
app.include_router(password_reset_routes.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})

@app.get("/", tags=["Plagiarism Check"])
async def root():
    return {"message": "Plagiarism Detection API is running."}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        upload_path = UPLOAD_DIR / file.filename
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        user_file = str(upload_path)
        resources = get_all_resources()
        total_result = []

        for resource in resources:
            reference_text = None
            file_path = resource.get("file_path")
            reference_name = resource.get("title", "Undefined Resource")
            try:
                if isinstance(file_path, str) and Path(file_path).exists():
                    reference_text = truetypealgorithm.read_file(file_path)
                    if isinstance(reference_text, list):
                        reference_text = "\n".join(reference_text)
                else:
                    file_url = resource.get("file_url")
                    if isinstance(file_url, str) and file_url:
                        response = requests.get(file_url)
                        if response.status_code == 200:
                            content_type = response.headers.get("Content-Type", "")
                            temp_path = UPLOAD_DIR / f"temp_{resource['id']}"
                            if "text/plain" in content_type:
                                reference_text = response.text
                            elif "application/pdf" in content_type:
                                temp_path = temp_path.with_suffix(".pdf")
                                with open(temp_path, "wb") as f:
                                    f.write(response.content)
                                reference_text = truetypealgorithm.read_file(str(temp_path))
                                temp_path.unlink()
                            elif "wordprocessingml.document" in content_type:
                                temp_path = temp_path.with_suffix(".docx")
                                with open(temp_path, "wb") as f:
                                    f.write(response.content)
                                reference_text = truetypealgorithm.read_file(str(temp_path))
                                temp_path.unlink()
                        # Skip if unsupported
                if isinstance(reference_text, str):
                    temp_ref = UPLOAD_DIR / f"temp_resource_{resource['id']}.txt"
                    temp_ref.write_text(reference_text, encoding="utf-8")
                    result = truetypealgorithm.get_plagiarism_report(user_file, str(temp_ref), display_name=reference_name)
                    total_result.append(result)
                    temp_ref.unlink()

            except Exception as sub_e:
                # Log minimal error
                print(f"⚠️ Resource error: {reference_name}")

        final_plag = total_score(total_result, user_file)
        final_plag = convert_np_types(final_plag)
        upload_path.unlink()
        return final_plag

    except Exception:
        traceback.print_exc()
        return {"error": "Failed to process uploaded file."}


def convert_np_types(obj):
    if isinstance(obj, dict):
        return {k: convert_np_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_np_types(i) for i in obj]
    elif isinstance(obj, np.ndarray):
        return [convert_np_types(i) for i in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    else:
        return obj


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"✅ Server ready at http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True, log_level="warning")
