from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import asyncio
import os
from app.models.responses import (
    HealthResponse, 
    DetailedHealthResponse,
    ReadinessResponse,
    LivenessResponse
)
from app.core.config import settings
from app.utils.logger import logger
from app.services.file_service import FileService  # Import FileService

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint
    
    Returns the current status of the API and its dependencies
    """
    try:
        services_status = {}
        
        # Check Gemini API availability
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            services_status["gemini"] = "healthy"
        except Exception as e:
            services_status["gemini"] = f"unhealthy: {str(e)}"
        
        # Check Manim availability
        try:
            import manim
            services_status["manim"] = "healthy"
        except Exception as e:
            services_status["manim"] = f"unhealthy: {str(e)}"
        
        # Check file system
        try:
            # Check if output directories exist and are writable
            output_dir = settings.output_dir
            if os.path.exists(output_dir) and os.access(output_dir, os.W_OK):
                services_status["filesystem"] = "healthy"
            else:
                services_status["filesystem"] = "unhealthy: output directory not writable"
        except Exception as e:
            services_status["filesystem"] = f"unhealthy: {str(e)}"
        
        # Overall status
        overall_status = "healthy" if all("healthy" in status for status in services_status.values()) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(),
            version="1.0.0",
            services=services_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            services={"error": str(e)}
        )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check with system information
    
    Returns comprehensive system and service status
    """
    try:
        import psutil
        import sys
        
        # System information
        system_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": os.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
        }
        
        # Service versions
        service_versions = {}
        
        try:
            import google.generativeai as genai
            service_versions["google-generativeai"] = genai.__version__
        except:
            service_versions["google-generativeai"] = "not available"
        
        try:
            import manim
            service_versions["manim"] = manim.__version__
        except:
            service_versions["manim"] = "not available"
        
        try:
            import fastapi
            service_versions["fastapi"] = fastapi.__version__
        except:
            service_versions["fastapi"] = "unknown"
        
        # Configuration check
        config_status = {
            "gemini_api_key_configured": bool(settings.gemini_api_key),
            "output_directory_exists": os.path.exists(settings.output_dir),
            "temp_directory_exists": os.path.exists(settings.temp_dir),
            "animation_directory_exists": os.path.exists(settings.animation_dir),
        }
        
        # File system stats
        try:
            file_service = FileService()
            storage_stats = file_service.get_storage_stats()
        except Exception as e:
            storage_stats = {"error": str(e)}
        
        return DetailedHealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            system_info=system_info,
            service_versions=service_versions,
            configuration=config_status,
            storage=storage_stats,
            settings={
                "debug": settings.debug,
                "animation_quality": settings.animation_quality,
                "max_animation_duration": settings.max_animation_duration,
                "max_requests_per_minute": settings.max_requests_per_minute,
            }
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        return DetailedHealthResponse(
            status="error",
            timestamp=datetime.now(),
            error=str(e)
        )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Kubernetes-style readiness check
    
    Returns 200 OK when the service is ready to accept requests
    """
    try:
        checks = []
        
        if not settings.gemini_api_key:
            checks.append("Gemini API key not configured")
        
        if not os.path.exists(settings.output_dir):
            checks.append("Output directory does not exist")
        
        try:
            import google.generativeai
            import manim
        except ImportError as e:
            checks.append(f"Required module not available: {e}")
        
        if checks:
            return ReadinessResponse(
                status="not ready",
                timestamp=datetime.now(),
                issues=checks
            )
        
        return ReadinessResponse(
            status="ready",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return ReadinessResponse(
            status="not ready",
            timestamp=datetime.now(),
            error=str(e)
        )


@router.get("/live", response_model=LivenessResponse)
async def liveness_check():
    """
    Kubernetes-style liveness check
    
    Returns 200 OK when the service is alive
    """
    return LivenessResponse(
        status="alive",
        timestamp=datetime.now()
    )