"""Schemas representing score requests and responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TimeSeriesData(BaseModel):
    """Time-series data for historical analytics and charts."""
    
    monthly: List[Dict[str, Any]] = Field(default_factory=list, description="Monthly aggregated metrics")
    weekly: List[Dict[str, Any]] = Field(default_factory=list, description="Weekly aggregated metrics")
    daily_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Daily transaction counts")
    hourly_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="Transaction count by hour")
    weekday_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="Transaction count by weekday")
    value_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="Transaction value buckets")
    cumulative: List[Dict[str, Any]] = Field(default_factory=list, description="Cumulative metrics over time")


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of score components."""

    credit_score: float = Field(
        ..., description="Final credit score between 0 and 1000"
    )
    features: Dict[str, Any] = Field(default_factory=dict)
    offchain_data: Dict[str, Any] = Field(default_factory=dict)
    card_info: Dict[str, Any] = Field(default_factory=dict)
    transaction_count: int = Field(default=0, ge=0)
    time_series: Optional[TimeSeriesData] = Field(default=None, description="Time-series analytics data")


class ScoreResponse(BaseModel):
    """Structured response returned by the API."""

    wallet_address: str
    breakdown: ScoreBreakdown
    message: Optional[str] = None


class ScoreRequest(BaseModel):
    """Incoming score request payload."""

    wallet_address: str = Field(..., min_length=42, max_length=42)
