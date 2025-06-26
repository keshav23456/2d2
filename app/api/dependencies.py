"""
Common dependencies for API routes
"""
from fastapi import Depends, HTTPException, status
from app.services.animation_service import AnimationService
from app.services.file_service import FileService
from app.utils.logger import logger


# Service instances
_animation_service = None
_file_service = None


def get_animation_service() -> AnimationService:
    """Dependency to get animation service instance"""
    global _animation_service
    if _animation_service is None:
        _animation_service = AnimationService()
    return _animation_service


def get_file_service() -> FileService:
    """Dependency to get file service instance"""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service


async def validate_task_id(task_id: str) -> str:
    """Validate task ID format"""
    if not task_id or len(task_id) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )
    return task_id


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 10, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests = {}
    
    async def check_rate_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit"""
        import time
        current_time = time.time()
        window_start = current_time - (self.window_minutes * 60)
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip] 
                if req_time > window_start
            ]
        else:
            self.requests[client_ip] = []
        
        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[client_ip].append(current_time)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(client_ip: str = None):
    """Rate limiting dependency"""
    if client_ip and not await rate_limiter.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    return True