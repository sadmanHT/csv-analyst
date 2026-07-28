"""
Streaming Query, Investigation, and Dataset Story Routes
"""

from fastapi import APIRouter
from backend.core.schemas import QueryRequest, StoryRequest, InvestigationRequest

query_router = APIRouter(tags=["Query & Analysis"])
