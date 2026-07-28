"""
Predictive Modeling, Scenario Simulation, Forecasting, and Dataset Comparison Routes
"""

from fastapi import APIRouter
from backend.core.schemas import PredictRequest, ForecastRequest, JoinRequest, CompareRequest, ScenarioRequest

model_router = APIRouter(tags=["Modeling & Forecasting"])
