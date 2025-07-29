# app/models/report_model.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ReportRequest(BaseModel):
    submitted_document: str
    unique_score: float
    total_exact_score: float
    total_partial_score: float
    words: Optional[int] = 0
    characters: Optional[int] = 0
    citation_status: Optional[str] = "unknown"

class ReportOut(BaseModel):
    id: int
    user_id: int
    submitted_document: str
    unique_score: float
    total_exact_score: float
    total_partial_score: float
    words: int
    characters: int
    citation_status: str
    created_at: datetime

class ReportHistoryOut(BaseModel):
    reports: List[ReportOut]
    pagination: dict

class ReportStatsOut(BaseModel):
    total_reports: int
    avg_unique_score: float
    avg_exact_score: float
    avg_partial_score: float
    first_report_date: Optional[datetime]
    latest_report_date: Optional[datetime]
