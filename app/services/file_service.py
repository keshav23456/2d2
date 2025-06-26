"""
File service for handling animation file operations
"""
import os
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import HTTPException
from fastapi.responses import FileResponse
from app.core.config import settings
from app.utils.logger import logger


class FileService:
    """Service for file operations and serving animations"""
    
    def __init__(self):
        """Initialize file service"""
        self.animation_dir = Path(settings.animation_dir)
        self.temp_dir = Path(settings.temp_dir)
        logger.info("Initialized File Service")
    
    async def get_animation_file(self, task_id: str) -> Optional[Path]:
        """
        Get animation file path for a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Path to animation file or None if not found
        """
        try:
            # Expected file name pattern
            expected_file = self.animation_dir / f"animation_{task_id}.mp4"
            
            if expected_file.exists():
                return expected_file
            
            # Search for files with task_id in name
            for file_path in self.animation_dir.glob(f"*{task_id}*"):
                if file_path.suffix.lower() in ['.mp4', '.mov', '.avi']:
                    return file_path
            
            logger.warning(f"Animation file not found for task: {task_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding animation file for task {task_id}: {str(e)}")
            return None
    
    def create_file_response(self, file_path: Path, task_id: str) -> FileResponse:
        """
        Create FastAPI FileResponse for animation download
        
        Args:
            file_path: Path to the animation file
            task_id: Task identifier for filename
            
        Returns:
            FileResponse for file download
        """
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Animation file not found")
        
        # Generate appropriate filename
        filename = f"animation_{task_id}.mp4"
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='video/mp4',
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    async def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get file information
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information
        """
        try:
            if not file_path.exists():
                return {"error": "File not found"}
            
            stat = file_path.stat()
            
            return {
                "file_name": file_path.name,
                "file_size": stat.st_size,
                "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "file_extension": file_path.suffix,
                "exists": True
            }
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {"error": str(e)}
    
    async def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            temp_files = list(self.temp_dir.glob("*"))
            cleaned_count = 0
            
            for temp_file in temp_files:
                try:
                    if temp_file.is_file():
                        temp_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} temporary files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {str(e)}")
            return 0
    
    async def cleanup_old_animations(self, days: int = 7):
        """
        Clean up animation files older than specified days
        
        Args:
            days: Number of days to keep files
            
        Returns:
            Number of files cleaned up
        """
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            animation_files = list(self.animation_dir.glob("*.mp4"))
            cleaned_count = 0
            
            for anim_file in animation_files:
                try:
                    if anim_file.stat().st_ctime < cutoff_time:
                        anim_file.unlink()
                        cleaned_count += 1
                        logger.info(f"Deleted old animation: {anim_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete old animation {anim_file}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} old animation files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during animation cleanup: {str(e)}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            animation_files = list(self.animation_dir.glob("*.mp4"))
            temp_files = list(self.temp_dir.glob("*"))
            
            animation_size = sum(f.stat().st_size for f in animation_files if f.is_file())
            temp_size = sum(f.stat().st_size for f in temp_files if f.is_file())
            
            return {
                "animation_count": len(animation_files),
                "animation_size_mb": round(animation_size / (1024 * 1024), 2),
                "temp_files_count": len(temp_files),
                "temp_size_mb": round(temp_size / (1024 * 1024), 2),
                "total_size_mb": round((animation_size + temp_size) / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {"error": str(e)}