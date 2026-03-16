# Visual Generator Agent - Creates images using Imagen
# Copyright 2026 Google LLC

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
import os

from app.agent_tools import sketch_scene
from app.app_utils.base_agent import TokenTrackingAgent

visual_generator_agent = TokenTrackingAgent(
    name="visual_generator_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=5, initial_delay=10.0, max_delay=60.0, exp_base=2.0, jitter=2.0, http_status_codes=[429, 503]),
    ),
    instruction="""You are the Visual Generator Agent. Generate images for story scenes by calling sketch_scene(prompt).
Always call the tool — never write placeholder text. Return the result directly.""",
    tools=[sketch_scene],
)
