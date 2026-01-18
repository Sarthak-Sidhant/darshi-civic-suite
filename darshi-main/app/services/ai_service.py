try:
    from google import genai
    from google.genai import types
    genai_available = True
except ImportError:
    genai_available = False
    genai = None
    types = None

import json
from app.core.config import settings
from app.models.schemas import AIAnalysisResult
from app.core.logging_config import get_logger
from app.core.exceptions import (
    AIServiceError,
    AIServiceUnavailableError,
    AIRateLimitError,
    AIQuotaExceededError,
    AITimeoutError,
    AIInvalidResponseError
)
from app.core.error_handling import (
    retry_ai_operation,
    circuit_breaker,
    ErrorContext
)

logger = get_logger(__name__)

if not genai_available:
    logger.warning("google-genai not installed, AI analysis will be disabled")

# Singleton Gemini model instance
_gemini_model = None

# System instruction for civic issue analysis (used for all requests)
CIVIC_ISSUE_SYSTEM_INSTRUCTION = """You are a civic issue classifier for a government grievance platform in India.

Your task is to analyze images of potential civic problems (potholes, garbage, broken streetlights, drainage issues, etc.) and provide structured analysis.

Return ONLY a raw JSON object (no markdown formatting) with these fields:
- is_valid (boolean): true if image shows a valid civic issue
- category (string): "Pothole", "Garbage", "Streetlight", "Drainage", "Road Damage", "Broken Infrastructure", "Public Space", "Other", or "None"
- severity (integer, 1-10): calculated using criteria below
- description (string): short description of the issue

## SEVERITY CALCULATION CRITERIA (1-10 scale):

**CRITICAL (9-10): Immediate danger to life or severe property damage**
- Deep potholes (>6 inches deep) on main roads or highways
- Complete road collapse or major structural failure
- Exposed live electrical wires on streetlights or poles
- Massive garbage accumulation blocking roads/footpaths
- Severe flooding blocking critical infrastructure
- Broken/missing manhole covers on busy roads
- Active fire hazards or gas leaks
- Fallen trees/poles blocking emergency routes

**HIGH (7-8): Significant safety risk or major inconvenience**
- Medium-deep potholes (3-6 inches) on frequently used roads
- Multiple broken streetlights in high-crime areas
- Large garbage piles creating health hazards (attracting pests)
- Broken traffic signals at busy intersections
- Damaged footpaths causing tripping hazards
- Water pipeline leaks causing road damage
- Dangerous cracks in bridges or overpasses
- Open drainage with overflowing sewage

**MEDIUM (5-6): Moderate inconvenience, needs timely attention**
- Shallow potholes (1-3 inches) on residential roads
- Single broken streetlight in moderately populated area
- Moderate garbage accumulation (not blocking path)
- Damaged road markings reducing visibility
- Minor drainage issues causing waterlogging
- Cracked/uneven pavements in public spaces
- Faded or missing traffic signs
- Overgrown vegetation obstructing view

**LOW (3-4): Minor inconvenience, cosmetic issues**
- Very small potholes or surface cracks
- Dim/flickering streetlights (still functional)
- Small garbage accumulation in designated areas
- Minor aesthetic damage to public property
- Graffiti on public walls (non-offensive)
- Slightly damaged benches or public furniture
- Minor littering in public spaces
- Small cracks in compound walls

**MINIMAL (1-2): Negligible impact, low priority**
- Cosmetic wear and tear on infrastructure
- Very minor surface damage
- Barely noticeable issues requiring no immediate action
- Minor discoloration or fading of paint

## SCORING FACTORS TO CONSIDER:
1. **Safety Risk**: Does this pose immediate danger to life/property?
2. **Location Context**: Is this on a busy road vs quiet residential area?
3. **Scale/Size**: How large is the problem (single vs multiple issues)?
4. **Accessibility Impact**: Does this block roads, footpaths, or emergency routes?
5. **Health Hazards**: Does this create hygiene/sanitation risks?
6. **Urgency**: How quickly does this need to be fixed?

If NOT a civic issue (personal photo, private property, no visible problem, too blurry):
- Set is_valid=false, severity=0, and explain why in description field.
"""


def get_gemini_model():
    """
    Get or create singleton Gemini model instance.

    Using a singleton saves initialization overhead and improves performance.

    Returns:
        Client instance configured for civic issue analysis
    """
    global _gemini_model

    if not genai_available:
        return None

    if not settings.GEMINI_API_KEY:
        return None

    if _gemini_model is None:
        try:
            _gemini_model = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Gemini client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)
            raise AIServiceError(
                message="Failed to initialize Gemini client",
                model="gemini-2.0-flash-exp",
                details=str(e)
            ) from e

    return _gemini_model

@retry_ai_operation(max_attempts=3)
@circuit_breaker(name="gemini_api", failure_threshold=5, recovery_timeout=120, expected_exception=AIServiceError)
def analyze_image(image_bytes: bytes) -> AIAnalysisResult:
    """
    Analyze an image using Google Gemini to determine if it contains a civic issue.

    Uses new google.genai client API.

    Args:
        image_bytes: The image file contents as bytes

    Returns:
        AIAnalysisResult with validation status, category, severity, and description

    Raises:
        AIServiceError: If AI analysis fails
        AIServiceUnavailableError: If AI service is unavailable
        AIRateLimitError: If rate limit is exceeded
        AITimeoutError: If request times out
    """
    client = get_gemini_model()

    if not client:
        raise AIServiceUnavailableError(
            message="AI service unavailable - Gemini not configured",
            model="gemini-2.0-flash-exp"
        )

    with ErrorContext("ai_service", "analyze_image", AIServiceError, model="gemini-2.0-flash-exp"):
        logger.debug(f"Starting AI analysis for image ({len(image_bytes)} bytes)")

        try:
            # Combine system instruction with user prompt
            full_prompt = f"""{CIVIC_ISSUE_SYSTEM_INSTRUCTION}

Analyze this image for civic issues and return JSON with is_valid, category, severity, and description fields."""

            logger.debug("Sending image to Gemini for analysis")

            # Generate content using new API with system instruction + image
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    types.Part.from_text(text=full_prompt),
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    )
                ]
            )

            # Extract text from response
            text = response.text
            logger.debug(f"Received Gemini response: {text[:200]}...")

            # Handle ```json ... ``` and just ``` ... ```
            if "```" in text:
                import re
                # Extract content inside code blocks
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
                if match:
                    text = match.group(1)
                    logger.debug("Stripped markdown code block wrapper from response")
            
            try:
                data = json.loads(text.strip())
            except json.JSONDecodeError as json_error:
                logger.warning(f"Invalid JSON response from Gemini: {json_error}. Response: {text[:200]}")
                raise AIInvalidResponseError(
                    message="AI returned invalid JSON response",
                    model="gemini-2.0-flash-exp",
                    details=f"JSON parse error: {str(json_error)}"
                ) from json_error

            # Validate response structure
            required_fields = ['is_valid', 'category', 'severity', 'description']
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                raise AIInvalidResponseError(
                    message=f"AI response missing required fields: {missing_fields}",
                    model="gemini-2.0-flash-exp"
                )

            # Ensure default values for robustness
            if "severity" not in data or data["severity"] is None:
                data["severity"] = 0

            result = AIAnalysisResult(**data)
            logger.info(f"AI analysis completed: is_valid={result.is_valid}, category={result.category}, severity={result.severity}")
            return result

        except AIInvalidResponseError:
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(f"Unexpected AI analysis error: {e}", exc_info=True)
            raise AIServiceError(
                message="Unexpected error during AI analysis",
                model="gemini-2.0-flash-exp",
                details=str(e)
            ) from e


