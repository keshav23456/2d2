"""
Main animation service that orchestrates the entire animation generation process
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from app.core.gemini_client import GeminiClient
from app.core.manim_processor import ManimProcessor
from app.models.requests import AnimationRequest
from app.models.responses import AnimationResponse, AnimationStatus, RefinedPrompt
from app.utils.logger import logger


class AnimationService:
    """Service for handling animation generation workflow"""
    
    def __init__(self):
        """Initialize animation service"""
        self.gemini_client = GeminiClient()
        self.manim_processor = ManimProcessor()
        self.tasks: Dict[str, Dict[str, Any]] = {}  # In-memory task storage
        logger.info("Initialized Animation Service")
    
    async def create_animation(self, request: AnimationRequest) -> AnimationResponse:
        """
        Start animation generation process
        
        Args:
            request: Animation request parameters
            
        Returns:
            Animation response with task ID
        """
        try:
            # Generate unique task ID
            task_id = str(uuid.uuid4())
            
            # Initialize task status
            self.tasks[task_id] = {
                'status': 'pending',
                'progress': 0,
                'message': 'Task created, waiting to start processing',
                'created_at': datetime.now(),
                'request': request.dict(),
                'file_url': None,
                'error_message': None
            }
            
            logger.info(f"Created animation task {task_id} with prompt: {request.prompt[:100]}...")
            
            # Start background processing
            asyncio.create_task(self._process_animation(task_id, request))
            
            return AnimationResponse(
                task_id=task_id,
                status='pending',
                message='Animation generation started. Use the task ID to check status.',
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error creating animation task: {str(e)}")
            raise Exception(f"Failed to create animation: {str(e)}")
    
    async def get_animation_status(self, task_id: str) -> Optional[AnimationStatus]:
        """
        Get status of animation generation task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Animation status or None if task not found
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        processing_time = None
        if task.get('completed_at') and task.get('created_at'):
            processing_time = (task['completed_at'] - task['created_at']).total_seconds()
        
        return AnimationStatus(
            task_id=task_id,
            status=task['status'],
            progress=task['progress'],
            message=task['message'],
            file_url=task.get('file_url'),
            error_message=task.get('error_message'),
            created_at=task['created_at'],
            completed_at=task.get('completed_at'),
            processing_time=processing_time
        )
    
    async def _process_animation(self, task_id: str, request: AnimationRequest):
        """
        Background task for processing animation generation
        
        Args:
            task_id: Task identifier
            request: Animation request parameters
        """
        try:
            logger.info(f"Starting processing for task {task_id}")
            
            # Step 1: Refine prompt with Gemini
            await self._update_task_status(task_id, 'processing', 10, 'Refining prompt with AI...')
            
            refined_result = await self.gemini_client.refine_prompt_and_generate_code(
                prompt=request.prompt,
                style=request.style,
                duration=request.duration or 10
            )
            
            logger.info(f"Prompt refined for task {task_id}")
            
            # Step 2: Generate animation with Manim
            await self._update_task_status(task_id, 'processing', 50, 'Generating animation...')
            
            animation_result = await self.manim_processor.generate_animation(
                manim_code=refined_result['manim_code'],
                task_id=task_id,
                quality=request.quality.value,
                background_color=request.background_color or "#000000"
            )
            
            if animation_result['success']:
                # Step 3: Finalize and complete
                await self._update_task_status(task_id, 'processing', 90, 'Finalizing animation...')
                
                # Store additional task data
                self.tasks[task_id].update({
                    'refined_prompt': refined_result,
                    'animation_result': animation_result,
                    'file_path': animation_result['file_path']
                })
                
                # Generate file URL (you might want to implement proper file serving)
                file_url = f"/api/animations/download/{task_id}"
                
                await self._update_task_status(
                    task_id, 
                    'completed', 
                    100, 
                    'Animation generated successfully!',
                    file_url=file_url
                )
                
                logger.info(f"Animation generation completed for task {task_id}")
                
            else:
                # Animation generation failed
                error_msg = animation_result.get('error', 'Unknown error in animation generation')
                await self._update_task_status(
                    task_id, 
                    'failed', 
                    0, 
                    'Animation generation failed',
                    error_message=error_msg
                )
                logger.error(f"Animation generation failed for task {task_id}: {error_msg}")
                
        except Exception as e:
            # Handle any unexpected errors
            error_msg = f"Unexpected error: {str(e)}"
            await self._update_task_status(
                task_id, 
                'failed', 
                0, 
                'Processing failed due to unexpected error',
                error_message=error_msg
            )
            logger.error(f"Unexpected error in task {task_id}: {str(e)}")
    
    async def _update_task_status(
        self, 
        task_id: str, 
        status: str, 
        progress: int, 
        message: str,
        file_url: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update task status in memory"""
        if task_id in self.tasks:
            self.tasks[task_id].update({
                'status': status,
                'progress': progress,
                'message': message,
                'updated_at': datetime.now()
            })
            
            if file_url:
                self.tasks[task_id]['file_url'] = file_url
            
            if error_message:
                self.tasks[task_id]['error_message'] = error_message
            
            if status in ['completed', 'failed']:
                self.tasks[task_id]['completed_at'] = datetime.now()
    
    async def get_refined_prompt(self, task_id: str) -> Optional[RefinedPrompt]:
        """
        Get refined prompt details for a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Refined prompt details or None if not found
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        refined_data = task.get('refined_prompt')
        
        if not refined_data:
            return None
        
        return RefinedPrompt(
            original_prompt=refined_data['original_prompt'],
            refined_prompt=refined_data['refined_prompt'],
            manim_code=refined_data['manim_code'],
            explanation=refined_data['explanation'],
            estimated_duration=refined_data.get('estimated_duration', 10)
        )
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all tasks (for admin/debugging purposes)"""
        return self.tasks
    
    def cleanup_old_tasks(self, hours: int = 24):
        """Clean up tasks older than specified hours"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            created_at = task['created_at'].timestamp()
            if created_at < cutoff_time:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            logger.info(f"Cleaned up old task: {task_id}")
        
        return len(tasks_to_remove)