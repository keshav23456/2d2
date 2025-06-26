"""
Manim animation processor for executing generated code and creating videos
"""
import os
import subprocess
import tempfile
import uuid
from typing import Optional, Dict, Any
import asyncio
from pathlib import Path
from app.core.config import settings
from app.utils.logger import logger


class ManimProcessor:
    """Processor for executing Manim code and generating animations"""
    
    def __init__(self):
        """Initialize Manim processor"""
        self.output_dir = Path(settings.animation_dir)
        self.temp_dir = Path(settings.temp_dir)
        logger.info("Initialized Manim Processor")
    
    async def generate_animation(
        self,
        manim_code: str,
        task_id: str,
        quality: str = "medium_quality",
        background_color: str = "#000000"
    ) -> Dict[str, Any]:
        """
        Generate animation from Manim code
        
        Args:
            manim_code: The Manim Python code to execute
            task_id: Unique task identifier
            quality: Animation quality setting
            background_color: Background color for animation
            
        Returns:
            Dictionary with generation results
        """
        try:
            logger.info(f"Starting animation generation for task {task_id}")
            
            # Prepare the code file
            code_file = await self._prepare_code_file(manim_code, task_id, background_color)
            
            # Execute Manim command
            output_path = await self._execute_manim(code_file, task_id, quality)
            
            # Verify output file exists
            if not output_path.exists():
                raise Exception("Animation file was not generated")
            
            # Get file information
            file_size = output_path.stat().st_size
            
            logger.info(f"Animation generated successfully for task {task_id}")
            
            return {
                'success': True,
                'file_path': str(output_path),
                'file_size': file_size,
                'task_id': task_id,
                'message': 'Animation generated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error generating animation for task {task_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'task_id': task_id,
                'message': f'Animation generation failed: {str(e)}'
            }
        finally:
            # Cleanup temporary files
            try:
                if 'code_file' in locals():
                    code_file.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")
    
    async def _prepare_code_file(self, manim_code: str, task_id: str, background_color: str) -> Path:
        """Prepare the Manim code file for execution"""
        
        # Clean and validate the code
        cleaned_code = self._clean_manim_code(manim_code, background_color)
        
        # Create temporary file
        code_file = self.temp_dir / f"animation_{task_id}.py"
        
        # Write code to file
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_code)
        
        logger.debug(f"Prepared code file: {code_file}")
        return code_file
    
    def _clean_manim_code(self, code: str, background_color: str) -> str:
        """Clean and enhance Manim code"""
        
        # Standard imports that should be included
        standard_imports = """from manim import *
import numpy as np
import math

"""
        
        # Check if code already has imports
        if "from manim import" not in code and "import manim" not in code:
            code = standard_imports + code
        
        # Ensure there's a scene class
        if "class " not in code or "Scene" not in code:
            # Wrap code in a basic scene
            code = f"""{standard_imports}

class GeneratedAnimation(Scene):
    def construct(self):
        # Set background color
        self.camera.background_color = "{background_color}"
        
        # Generated animation code
{self._indent_code(code, 8)}
"""
        else:
            # Just add background color setting
            if "background_color" not in code:
                # Find the construct method and add background color
                lines = code.split('\n')
                for i, line in enumerate(lines):
                    if "def construct(self):" in line:
                        lines.insert(i + 1, f'        self.camera.background_color = "{background_color}"')
                        break
                code = '\n'.join(lines)
        
        return code
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces"""
        indent = ' ' * spaces
        return '\n'.join(indent + line if line.strip() else line for line in code.split('\n'))
    
    async def _execute_manim(self, code_file: Path, task_id: str, quality: str) -> Path:
        """Execute Manim command to generate animation"""
        
        # Determine output file name
        output_filename = f"animation_{task_id}.mp4"
        output_path = self.output_dir / output_filename
        
        # Build Manim command
        cmd = [
            "manim",
            str(code_file),
            "--format=mp4",
            f"--quality={quality}",
            f"--output_file={output_filename}",
            "--disable_caching",
            "--flush_cache"
        ]
        
        logger.info(f"Executing Manim command: {' '.join(cmd)}")
        
        try:
            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.output_dir)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown Manim error"
                logger.error(f"Manim execution failed: {error_msg}")
                raise Exception(f"Manim execution failed: {error_msg}")
            
            logger.info(f"Manim execution completed successfully")
            
            # Find the generated file (Manim might create subdirectories)
            generated_file = self._find_generated_file(task_id)
            if generated_file and generated_file != output_path:
                # Move file to expected location
                generated_file.rename(output_path)
            
            return output_path
            
        except asyncio.TimeoutError:
            raise Exception("Manim execution timed out")
        except Exception as e:
            raise Exception(f"Failed to execute Manim: {str(e)}")
    
    def _find_generated_file(self, task_id: str) -> Optional[Path]:
        """Find the generated animation file"""
        
        # Common patterns where Manim might place files
        search_patterns = [
            f"animation_{task_id}.mp4",
            f"*{task_id}*.mp4",
            "*.mp4"
        ]
        
        search_dirs = [
            self.output_dir,
            self.output_dir / "videos",
            self.output_dir / "videos" / "1080p60",
            self.output_dir / "videos" / "720p30",
            self.output_dir / "videos" / "480p15"
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            for pattern in search_patterns:
                files = list(search_dir.glob(pattern))
                if files:
                    # Return the most recent file
                    return max(files, key=lambda f: f.stat().st_mtime)
        
        return None
    
    async def get_animation_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about generated animation"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {'error': 'File not found'}
            
            stat = path.stat()
            
            return {
                'file_size': stat.st_size,
                'created_at': stat.st_ctime,
                'modified_at': stat.st_mtime,
                'file_path': str(path),
                'file_name': path.name,
                'file_extension': path.suffix
            }
        except Exception as e:
            logger.error(f"Error getting animation info: {e}")
            return {'error': str(e)}