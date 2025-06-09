
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, example="Input text to analyze")


class PersonalityProfile(BaseModel):
    openness: float = Field(..., ge=0.0, le=1.0)
    conscientiousness: float = Field(..., ge=0.0, le=1.0)
    extraversion: float = Field(..., ge=0.0, le=1.0)
    agreeableness: float = Field(..., ge=0.0, le=1.0)
    neuroticism: float = Field(..., ge=0.0, le=1.0)
    mbti_type: str = Field(..., example="INFP")
    tone_analysis: str = Field(..., example="Reflective and introspective")
    writing_style: str = Field(..., example="Analytical and thoughtful")
    summary: str = Field(..., example="A thoughtful individual with...")


class APIResponse(BaseModel):
    success: bool
    timestamp: datetime
    error: Optional[str] = None
    response: Optional[PersonalityProfile] = None
