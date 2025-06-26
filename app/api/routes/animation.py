"""
Animation API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse
from typing import Dict, Any
from app.models.requests import AnimationRequest
from app.models.responses import AnimationResponse, AnimationStatus, RefinedPrompt, ErrorResponse
from app.services.animation_service import AnimationService
from app.services.file_service import FileService
from app.api.dependencies import (
    get_animation_service, 
    get_file_service, 
    validate_task_id,
    check_rate_limit
)
from app.utils.logger import logger

router = APIRouter(prefix="/api/animations", tags=["animations"])


@router.post("/generate", response_model=AnimationResponse)
async def generate_animation(
    request: AnimationRequest,
    http_request: Request,
    animation_service: AnimationService = Depends(get_animation_service),
    _: bool = Depends(check_rate_limit)
):
    """
    Generate a new animation from a text prompt
    
    - **prompt**: Description of the animation to generate
    - **style**: Animation style (mathematical, educational, scientific, presentation, creative)
    - **quality**: Animation quality (low, medium, high, ultra)
    - **duration**: Animation duration in seconds (5-30)
    - **background_color**: Background color in hex format
    - **include_audio**: Whether to include audio narration (not yet implemented)
    """
    try:
        # Get client IP for rate limiting
        client_ip = http_request.client.host
        await check_rate_limit(client_ip)
        
        logger.info(f"Animation generation request from {client_ip}: {request.prompt[:100]}...")
        
        response = await animation_service.create_animation(request)
        
        logger.info(f"Animation task created: {response.task_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error in generate_animation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate animation: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=AnimationStatus)
async def get_animation_status(
    task_id: str = Depends(validate_task_id),
    animation_service: AnimationService = Depends(get_animation_service)
):
    """
    Get the status of an animation generation task
    
    - **task_id**: The unique task identifier returned when creating the animation
    
    Status values:
    - **pending**: Task is waiting to be processed
    - **processing**: Task is currently being processed
    - **completed**: Animation has been generated successfully
    - **failed**: Animation generation failed
    """
    try:
        status = await animation_service.get_animation_status(task_id)
        
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting animation status for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get animation status"
        )


@router.get("/download/{task_id}")
async def download_animation(
    task_id: str = Depends(validate_task_id),
    animation_service: AnimationService = Depends(get_animation_service),
    file_service: FileService = Depends(get_file_service)
):
    """
    Download the generated animation file
    
    - **task_id**: The unique task identifier
    
    Returns the animation file as MP4 download
    """
    try:
        # Check if task exists and is completed
        task_status = await animation_service.get_animation_status(task_id)
        
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task_status.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Animation is not ready. Current status: {task_status.status}"
            )
        
        # Get animation file
        file_path = await file_service.get_animation_file(task_id)
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Animation file not found"
            )
        
        logger.info(f"Serving animation download for task: {task_id}")
        
        return file_service.create_file_response(file_path, task_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading animation for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download animation"
        )


@router.get("/refined-prompt/{task_id}", response_model=RefinedPrompt)
async def get_refined_prompt(
    task_id: str = Depends(validate_task_id),
    animation_service: AnimationService = Depends(get_animation_service)
):
    """
    Get the refined prompt and generated Manim code for a task
    
    - **task_id**: The unique task identifier
    
    Returns the original prompt, refined prompt, generated Manim code, and explanation
    """
    try:
        refined_prompt = await animation_service.get_refined_prompt(task_id)
        
        if not refined_prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or prompt not yet processed"
            )
        
        return refined_prompt
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting refined prompt for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get refined prompt"
        )


@router.get("/list")
async def list_animations(
    animation_service: AnimationService = Depends(get_animation_service)
) -> Dict[str, Any]:
    """
    List all animation tasks (for debugging/admin purposes)
    
    Returns a dictionary of all tasks with their current status
    """
    try:
        tasks = animation_service.get_all_tasks()
        
        # Return simplified view
        simplified_tasks = {}
        for task_id, task_data in tasks.items():
            simplified_tasks[task_id] = {
                'status': task_data['status'],
                'progress': task_data['progress'],
                'message': task_data['message'],
                'created_at': task_data['created_at'].isoformat(),
                'prompt': task_data['request']['prompt'][:100] + '...' if len(task_data['request']['prompt']) > 100 else task_data['request']['prompt']
            }
        
        return {
            'total_tasks': len(simplified_tasks),
            'tasks': simplified_tasks
        }
        
    except Exception as e:
        logger.error(f"Error listing animations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list animations"
        )


@router.delete("/cleanup")
async def cleanup_old_tasks(
    hours: int = 24,
    animation_service: AnimationService = Depends(get_animation_service),
    file_service: FileService = Depends(get_file_service)
) -> Dict[str, Any]:
    """
    Clean up old tasks and files
    
    - **hours**: Remove tasks older than this many hours (default: 24)
    
    Returns cleanup statistics
    """
    try:
        # Clean up old tasks
        cleaned_tasks = animation_service.cleanup_old_tasks(hours)
        
        # Clean up old files
        cleaned_files = await file_service.cleanup_old_animations(days=hours//24 or 1)
        
        # Clean up temp files
        cleaned_temp = await file_service.cleanup_temp_files()
        
        return {
            'cleaned_tasks': cleaned_tasks,
            'cleaned_animation_files': cleaned_files,
            'cleaned_temp_files': cleaned_temp,
            'message': f'Cleanup completed. Removed {cleaned_tasks} tasks, {cleaned_files} animation files, and {cleaned_temp} temp files.'
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform cleanup"
        )


@router.get("/storage-stats")
async def get_storage_stats(
    file_service: FileService = Depends(get_file_service)
) -> Dict[str, Any]:
    """
    Get storage usage statistics
    
    Returns information about disk usage for animations and temporary files
    """
    try:
        stats = file_service.get_storage_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting storage stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get storage statistics"
        )