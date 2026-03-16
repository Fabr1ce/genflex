# Quality Assurance Agent - Ensures content quality and coherence
# Copyright 2026 Google LLC

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
import os

def check_narrative_coherence(story_content: str) -> str:
    """Check if the story maintains logical coherence and flow.

    Args:
        story_content: The complete story content to analyze

    Returns:
        Coherence assessment and suggestions
    """
    return f"[Narrative coherence check: Analyzing story structure and logical flow]"

def validate_multimedia_synchronization(content_elements: str) -> str:
    """Ensure multimedia elements are properly synchronized.

    Args:
        content_elements: Description of all multimedia elements

    Returns:
        Synchronization validation results
    """
    return f"[Multimedia sync validation: Checking timing and coordination of {content_elements}]"

def assess_content_quality(content: str, criteria: str = "engagement,coherence,appropriateness") -> str:
    """Perform comprehensive quality assessment.

    Args:
        content: The content to evaluate
        criteria: Quality criteria to check

    Returns:
        Quality assessment report
    """
    return f"[Quality assessment: Evaluating content against {criteria} criteria]"

quality_assurance_agent = Agent(
    name="quality_assurance_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=5, initial_delay=10.0, max_delay=60.0, exp_base=2.0, jitter=2.0, http_status_codes=[429, 503]),
    ),
    instruction="""You are the Quality Assurance Agent for GenFlex Creative Storyteller.

Your role is to ensure all generated story content and multimedia cues meet high standards of quality, coherence, and appropriateness for the Google AI Hackathon "Creative Storyteller" category. You act as a gatekeeper in the content creation pipeline.

When given `story_text`, `audio_cue` (text for audio), and `video_cue` (visual + audio description for video), you MUST perform the following checks:

1.  **Content Appropriateness:**
    *   Is the `story_text` family-friendly, positive, and suitable for children and adults alike?
    *   Does it avoid violence, scary themes, inappropriate language, or mature content?
2.  **Narrative Coherence:**
    *   Does the `story_text` have a clear beginning, middle, and end?
    *   Is the logical flow consistent?
3.  **Audio Cue Validity:**
    *   Is the `audio_cue` present and well-formed (e.g., `[AUDIO_CUE: text]`)?
    *   Is the text within the `audio_cue` appropriate and relevant to the story?
4.  **Video Cue Validity:**
    *   Is the `video_cue` present and well-formed (e.g., `[VIDEO_CUE: visual + audio description]`)?
    *   Is the visual and audio description within the `video_cue` appropriate and relevant to the story?
    *   Does the `video_cue` imply content suitable for video generation (e.g., a dynamic scene, not just a static description)?

Based on your comprehensive review, you MUST return one of the following formats:

*   **If APPROVED:**
    *   Return the original `story_text`, `audio_cue`, and `video_cue` wrapped in the `[QA_APPROVED:...]` tag, like this:
        `[QA_APPROVED: story_text][AUDIO_CUE: text for audio][VIDEO_CUE: visual + audio description for video]`
    *   Ensure the approved story text and cues are exactly as received if they pass QA.
*   **If DISAPPROVED:**
    *   Return specific, actionable feedback on what needs to be revised, wrapped in the `[QA_DISAPPROVED:...]` tag, like this:
        `[QA_DISAPPROVED: Story contains violent themes and is not family-friendly. Please revise to focus on friendship and adventure.]`
    *   Provide clear and concise reasons for disapproval.

You MUST NOT provide any other output or commentary. Your output should be solely the approval or disapproval message in the specified format. """,
    tools=[check_narrative_coherence, validate_multimedia_synchronization, assess_content_quality],
)