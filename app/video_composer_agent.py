# Video Composer Agent - Creates video using Veo
# Copyright 2026 Google LLC

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
import os

from app.agent_tools import create_video_segment
from app.app_utils.base_agent import TokenTrackingAgent

video_composer_agent = TokenTrackingAgent(
    name="video_composer_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=5, initial_delay=10.0, max_delay=60.0, exp_base=2.0, jitter=2.0, http_status_codes=[429, 503]),
    ),
    instruction="""You are the Video Composer Agent. Generate video clips by calling create_video_segment(image_prompt, narration, duration).
Always call the tool — never write placeholder text. Return the result directly.""",
    tools=[create_video_segment],
)
