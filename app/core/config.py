"""
Configuration settings for the animation backend
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # API Configuration
    app_name: str = Field(default="Animation Generator API", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Gemini AI Configuration
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", env="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.7, env="GEMINI_TEMPERATURE")
    gemini_max_tokens: int = Field(default=2048, env="GEMINI_MAX_TOKENS")
    
    # File Paths
    output_dir: str = Field(default="outputs", env="OUTPUT_DIR")
    temp_dir: str = Field(default="outputs/temp", env="TEMP_DIR")
    animation_dir: str = Field(default="outputs/animations", env="ANIMATION_DIR")
    template_dir: str = Field(default="templates", env="TEMPLATE_DIR")
    
    # Animation Settings
    animation_quality: str = Field(default="medium_quality", env="ANIMATION_QUALITY")
    animation_format: str = Field(default="mp4", env="ANIMATION_FORMAT")
    max_animation_duration: int = Field(default=30, env="MAX_ANIMATION_DURATION")  # seconds
    
    # Rate limiting
    max_requests_per_minute: int = Field(default=10, env="MAX_REQUESTS_PER_MINUTE")
    
    # Redis Configuration (for task queue)
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Security
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.output_dir, exist_ok=True)
os.makedirs(settings.temp_dir, exist_ok=True)
os.makedirs(settings.animation_dir, exist_ok=True)
os.makedirs(settings.template_dir, exist_ok=True)