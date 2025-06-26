"""
Gemini AI client for prompt refinement and Manim code generation
"""
import google.generativeai as genai
from typing import Optional
import json
from app.core.config import settings
from app.utils.logger import logger
from app.models.requests import AnimationStyle


class GeminiClient:
    """Client for interacting with Google Gemini AI"""
    
    def __init__(self):
        """Initialize Gemini client"""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        logger.info(f"Initialized Gemini client with model: {settings.gemini_model}")
    
    async def refine_prompt_and_generate_code(
        self, 
        prompt: str, 
        style: AnimationStyle = AnimationStyle.EDUCATIONAL,
        duration: int = 10
    ) -> dict:
        """
        Refine user prompt and generate Manim code
        
        Args:
            prompt: User's animation description
            style: Animation style
            duration: Desired duration in seconds
            
        Returns:
            Dictionary with refined prompt and Manim code
        """
        try:
            logger.info(f"Processing prompt with Gemini: {prompt[:100]}...")
            
            system_prompt = self._get_system_prompt(style, duration)
            full_prompt = f"{system_prompt}\n\nUser Request: {prompt}"
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.gemini_temperature,
                    max_output_tokens=settings.gemini_max_tokens,
                )
            )
            
            if not response.text:
                raise Exception("Empty response from Gemini")
            
            # Parse the structured response
            result = self._parse_response(response.text)
            result['original_prompt'] = prompt
            
            logger.info("Successfully generated refined prompt and Manim code")
            return result
            
        except Exception as e:
            logger.error(f"Error in Gemini processing: {str(e)}")
            raise Exception(f"Failed to process prompt with Gemini: {str(e)}")
    
    def _get_system_prompt(self, style: AnimationStyle, duration: int) -> str:
        """Generate system prompt based on animation style"""
        
        base_prompt = f"""You are an expert Manim (Mathematical Animation Engine) developer. Your task is to:

1. Refine the user's prompt to be more specific and animation-friendly
2. Generate working Manim code that creates the requested animation
3. Ensure the animation duration is approximately {duration} seconds

Animation Style: {style.value}

Requirements:
- Generate complete, executable Manim code
- Use proper Manim syntax and imports
- Include appropriate animations and transitions
- Code should be production-ready
- Animation should be visually appealing and smooth
- Use colors and styling appropriate for {style.value} content

Response Format (JSON):
{{
    "refined_prompt": "Detailed, specific description of the animation",
    "manim_code": "Complete Manim Python code",
    "explanation": "Brief explanation of what the animation does",
    "estimated_duration": {duration},
    "key_elements": ["list", "of", "main", "visual", "elements"]
}}

Style-specific guidelines:"""

        style_guidelines = {
            AnimationStyle.MATHEMATICAL: """
- Focus on mathematical concepts, equations, graphs
- Use mathematical notation and symbols
- Include step-by-step derivations or proofs
- Use colors that highlight mathematical relationships
- Consider geometric transformations and algebraic manipulations
""",
            AnimationStyle.EDUCATIONAL: """
- Create clear, easy-to-follow explanations
- Use simple, clean visuals
- Include text explanations alongside visuals
- Build concepts progressively
- Use educational color schemes (blues, greens)
""",
            AnimationStyle.SCIENTIFIC: """
- Focus on scientific accuracy and precision
- Use scientific notation and units
- Include data visualizations, charts, diagrams
- Use professional color schemes
- Show cause-and-effect relationships
""",
            AnimationStyle.PRESENTATION: """
- Create polished, professional-looking animations
- Use corporate-friendly colors and fonts
- Focus on clear messaging and key points
- Include smooth transitions and engaging visuals
- Emphasize important information
""",
            AnimationStyle.CREATIVE: """
- Use vibrant colors and creative visual effects
- Include artistic elements and creative transitions
- Experiment with unique visual styles
- Focus on visual appeal and engagement
- Use creative typography and design elements
"""
        }
        
        return base_prompt + style_guidelines.get(style, style_guidelines[AnimationStyle.EDUCATIONAL])
    
    def _parse_response(self, response_text: str) -> dict:
        """Parse Gemini response into structured format"""
        try:
            # Try to extract JSON from the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise Exception("No JSON found in response")
            
            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['refined_prompt', 'manim_code', 'explanation']
            for field in required_fields:
                if field not in result:
                    raise Exception(f"Missing required field: {field}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            # Fallback: try to extract code blocks
            return self._fallback_parse(response_text)
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            raise Exception(f"Failed to parse Gemini response: {str(e)}")
    
    def _fallback_parse(self, response_text: str) -> dict:
        """Fallback parsing when JSON parsing fails"""
        # Extract code blocks
        code_start = response_text.find('```python')
        if code_start == -1:
            code_start = response_text.find('```')
        
        if code_start != -1:
            code_end = response_text.find('```', code_start + 3)
            if code_end != -1:
                manim_code = response_text[code_start:code_end + 3]
                manim_code = manim_code.strip('`').strip()
                if manim_code.startswith('python\n'):
                    manim_code = manim_code[7:]
            else:
                manim_code = "# Failed to extract code"
        else:
            manim_code = "# No code found in response"
        
        return {
            'refined_prompt': "Refined prompt extraction failed",
            'manim_code': manim_code,
            'explanation': response_text[:500] + "..." if len(response_text) > 500 else response_text,
            'estimated_duration': 10,
            'key_elements': ['animation', 'visual', 'content']
        }