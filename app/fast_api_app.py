from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

# Set global logging level to DEBUG
logging.basicConfig(level=logging.DEBUG)

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import google.auth.exceptions

import re

def _extract_media_parts(text: str) -> list[dict]:
    """Parse [IMAGE: uri], [AUDIO: uri], [VIDEO: uri] tags out of tool result text."""
    results = []
    pattern = re.compile(r'\[(IMAGE|AUDIO|VIDEO):\s*([^\]]+)\]')
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            chunk = text[last:m.start()].strip()
            if chunk:
                results.append({"type": "text", "value": chunk})
        kind, uri = m.group(1), m.group(2).strip()
        
        # Convert gs:// URLs to public HTTPS URLs for the frontend
        if uri.startswith("gs://"):
            uri = uri.replace("gs://", "https://storage.googleapis.com/", 1)
            
        results.append({"type": kind.lower(), "value": uri})
        last = m.end()
    if last < len(text):
        chunk = text[last:].strip()
        if chunk:
            results.append({"type": "text", "value": chunk})
    return results if results else [{"type": "text", "value": text}]


def _realize_media_placeholders(parts: list[dict]) -> list[dict]:
    """Replace [VISUAL_SCENE:], [AUDIO_MOMENT:], [VIDEO_SEQUENCE:] placeholders
    the model writes as text with actual generated media."""
    from app.agent_tools import sketch_scene, generate_audio_narration

    placeholder = re.compile(
        r'\[(VISUAL_SCENE|AUDIO_MOMENT|VIDEO_SEQUENCE):\s*([^\]]+)\]',
        re.IGNORECASE
    )
    realized = []
    for part in parts:
        if part.get("type") != "text":
            realized.append(part)
            continue

        text = part.get("value", "")
        last = 0
        for m in placeholder.finditer(text):
            before = text[last:m.start()].strip()
            if before:
                realized.append({"type": "text", "value": before})
            kind = m.group(1).upper()
            desc = m.group(2).strip()
            if kind == "VISUAL_SCENE":
                result = sketch_scene(desc)
                realized.extend(_extract_media_parts(result))
            elif kind == "AUDIO_MOMENT":
                result = generate_audio_narration(desc)
                realized.extend(_extract_media_parts(result))
            else:  # VIDEO_SEQUENCE — skip, too slow for inline
                realized.append({"type": "text", "value": f"[Video: {desc}]"})
            last = m.end()
        remainder = text[last:].strip()
        if remainder:
            realized.append({"type": "text", "value": remainder})
    return realized


from app.app_utils.token_tracker import get_token_tracker
from app.app_utils.logging_config import setup_logging
from app.agent import root_agent

import redis
import os

setup_logging()

# Initialize Redis client using environment variables
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
try:
    redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, socket_connect_timeout=5)
    redis_client.ping() # Test connection
    logging.info(f"Connected to Redis at {redis_host}:{redis_port}")
except redis.exceptions.ConnectionError as e:
    logging.error(f"Could not connect to Redis at {redis_host}:{redis_port}: {e}")
    redis_client = None # Set to None if connection fails

app = FastAPI(title="GenFlex Storyteller API", description="Multimodal Creative Storyteller for Google AI Hackathon")

@app.get("/redis-test")
async def redis_test():
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not connected")
    try:
        test_key = "mytestkey"
        test_value = "Hello from Redis!"
        redis_client.set(test_key, test_value)
        retrieved_value = redis_client.get(test_key)
        if retrieved_value and retrieved_value.decode() == test_value:
            return {"status": "success", "message": "Redis connection and R/W test successful!", "retrieved_value": retrieved_value.decode()}
        else:
            raise HTTPException(status_code=500, detail="Redis read/write failed or value mismatch")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis operation failed: {e}")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize token tracker
token_tracker = get_token_tracker()

# Stateless runner helper (in-memory session + runner).
# Use async methods to avoid deprecated sync helpers.
session_service = InMemorySessionService()
session = None
runner = None


@app.on_event("startup")
async def _startup() -> None:
    global session, runner
    session = await session_service.create_session(user_id="api_user", app_name="api")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="api")


class StoryRequest(BaseModel):
    prompt: str


class StoryResponse(BaseModel):
    parts: list[dict]
    token_usage: dict


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    """Serve the main web interface."""
    return FileResponse("static/index.html", media_type="text/html")


@app.post("/story", response_model=StoryResponse)
async def generate_story(req: StoryRequest):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    # Track initial token count for this request
    initial_session_tokens = token_tracker.session_tokens

    # run asynchronously to avoid deprecated APIs
    try:
        events = runner.run_async(
            user_id="api_user",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=req.prompt)]),
            run_config=RunConfig(streaming_mode=StreamingMode.NONE),
        )

        media_items = {}
        media_errors = {}
        story_text = ""
        inline_parts = []
        
        async for event in events:
            # Log agent reasoning and actions
            if not getattr(event, "is_final_response", lambda: False)():
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            logging.debug(f"Agent Thought ({event.author}): {part.text.strip()}")
                if event.actions:
                    for action in event.actions:
                        if action and hasattr(action, '__getitem__') and len(action) > 0 and hasattr(action[0], 'function_call'):
                            logging.debug(f"Agent Tool Call ({event.author}): {action[0].function_call.name}({action[0].function_call.args})")

            # Original logic for processing tool responses and final content
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # 1. Look for tool responses (from sub-agents) across ALL events
                    func_resp = getattr(part, "function_response", None)
                    if func_resp:
                        resp = getattr(func_resp, "response", None) or {}
                        resp_text = str(resp.get("output") or resp.get("result") or resp)
                        for m in re.finditer(r'\[(IMAGE|AUDIO|VIDEO):\s*([^\]]+)\]', resp_text):
                            uri = m.group(2).strip()
                            if uri.startswith("gs://"):
                                uri = uri.replace("gs://", "https://storage.googleapis.com/", 1)
                            media_items[m.group(1).lower()] = uri
                        for m in re.finditer(r'\[(IMAGE_ERROR|AUDIO_ERROR|VIDEO_ERROR|VIDEO_SKIPPED)[^\]]*\]', resp_text):
                            media_errors[m.group(1).split('_')[0].lower()] = "[Multimedia unavailable]"

                    # 2. Capture the final text from the final event only
                    if getattr(event, "is_final_response", lambda: False)():
                        text = getattr(part, "text", None)
                        inline = getattr(part, "inline_data", None)
                        if text:
                            story_text += text + "\n"
                        if inline:
                            inline_parts.append({
                                "type": inline.mime_type.split("/")[0] if inline.mime_type else "text",
                                "value": f"data:{inline.mime_type};base64,{__import__('base64').b64encode(inline.data).decode()}",
                            })

        # Clean the final story text by removing any inline tags left over by the LLM
        clean_story_text = re.sub(r'\[(IMAGE|AUDIO|VIDEO|IMAGE_ERROR|AUDIO_ERROR|VIDEO_ERROR|VIDEO_SKIPPED)[^\]]*\]', '', story_text)
        clean_story_text = re.sub(r'\[QA_[A-Z]+:[^\]]+\]', '', clean_story_text)
        clean_story_text = clean_story_text.strip()

        parts = []
        # Build strictly ordered UI parts: Image -> Text -> Audio -> Video
        for media_type in ['image']:
            if media_type in media_items: parts.append({"type": media_type, "value": media_items[media_type]})
            elif media_type in media_errors: parts.append({"type": media_type, "value": media_errors[media_type]})
        
        if clean_story_text:
            parts.append({"type": "text", "value": clean_story_text})
            
        for media_type in ['audio', 'video']:
            if media_type in media_items: parts.append({"type": media_type, "value": media_items[media_type]})
            elif media_type in media_errors: parts.append({"type": media_type, "value": media_errors[media_type]})
            
        parts.extend(inline_parts)

        # Calculate tokens used in this request
        tokens_used = token_tracker.session_tokens - initial_session_tokens

        # Prepare token usage response
        token_usage = {
            "tokens_used": tokens_used,
            "session_total": token_tracker.session_tokens,
            "cumulative_total": token_tracker.total_tokens,
            "model": "gemini-2.5-flash"
        }

        return StoryResponse(parts=parts, token_usage=token_usage)
    except Exception as e:
        if (
            isinstance(e, google.auth.exceptions.TransportError)
            or isinstance(e, google.auth.exceptions.DefaultCredentialsError)
            or "oauth2.googleapis.com" in str(e)
        ):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Authentication error: unable to reach Google OAuth endpoints. "
                    "Please run `gcloud auth login` (or `gcloud auth application-default login`) and retry."
                ),
            )
        raise


@app.get("/token-stats")
async def get_token_stats(days: int = 7):
    """Get token usage statistics for the specified number of days."""
    try:
        stats = token_tracker.get_usage_stats(days)
        return {
            "stats": stats,
            "period_days": days,
            "timestamp": "2026-03-14T00:00:00Z"  # Current date
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve token stats: {str(e)}")


@app.post("/reset-session-tokens")
async def reset_session_tokens():
    """Reset the session token counter."""
    try:
        token_tracker.reset_session()
        return {"message": "Session token counter reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset session tokens: {str(e)}")
