
"""
Pydantic models for request/response validation
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime


class AnimationStyle(str, Enum):
    """Animation style options"""
    MATHEMATICAL = "mathematical"
    EDUCATIONAL = "educational"
    SCIENTIFIC = "scientific"
    PRESENTATION = "presentation"
    CREATIVE = "creative"


class AnimationQuality(str, Enum):
    """Animation quality options"""
    LOW = "low_quality"
    MEDIUM = "medium_quality"
    HIGH = "high_quality"
    ULTRA = "production_quality"


class AnimationRequest(BaseModel):
    """Request model for animation generation"""
    prompt: str = Field(..., min_length=10, max_length=2000, description="Description of the animation to generate")
    style: AnimationStyle = Field(default=AnimationStyle.EDUCATIONAL, description="Animation style")
    quality: AnimationQuality = Field(default=AnimationQuality.MEDIUM, description="Animation quality")
    duration: Optional[int] = Field(default=10, ge=5, le=30, description="Animation duration in seconds")
    background_color: Optional[str] = Field(default="#000000", description="Background color (hex format)")
    include_audio: bool = Field(default=False, description="Whether to include audio narration")
    
    @validator('background_color')
    def validate_color(cls, v):
        if v and not v.startswith('#') or len(v) != 7:
            raise ValueError('Background color must be in hex format (#RRGGBB)')
        return v


class AnimationResponse(BaseModel):
    """Response model for animation generation"""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(default_factory=datetime.now)


class AnimationStatus(BaseModel):
    """Model for animation status check"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int = Field(ge=0, le=100, description="Progress percentage")
    message: str
    file_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None  # seconds


class RefinedPrompt(BaseModel):
    """Model for refined prompt from Gemini"""
    original_prompt: str
    refined_prompt: str
    manim_code: str
    explanation: str
    estimated_duration: int


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    services: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None