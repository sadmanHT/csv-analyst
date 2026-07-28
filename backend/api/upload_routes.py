"""
File, Text, URL, and Document Upload Routes
"""

import io
import json
import base64
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Header, Query
from backend.core.config import MAX_UPLOAD_BYTES
from backend.core.schemas import TextUploadRequest, UrlImportRequest

upload_router = APIRouter(tags=["Upload"])

@upload_router.get("/health")
def health() -> dict:
    return {"status": "ok"}
