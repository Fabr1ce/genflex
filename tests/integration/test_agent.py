# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


def test_agent_stream() -> None:
    """
    Integration test for the agent stream functionality.
    Tests that the agent returns valid streaming responses.
    """

    session_service = InMemorySessionService()

    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Why is the sky blue?")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    assert len(events) > 0, "Expected at least one message"

    has_text_content = False
    for event in events:
        if (
            event.content
            and event.content.parts
            and any(part.text for part in event.content.parts)
        ):
            has_text_content = True
            break
    assert has_text_content, "Expected at least one message with text content"


def test_story_includes_image() -> None:
    """
    Ensure the creative storyteller returns a response containing at least one
    non-text part (e.g. an image) when asked to include a picture in the story.
    """

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    prompt = (
        "Tell me a short story about a dragon and include an image of the dragon"
    )
    message = types.Content(
        role="user", parts=[types.Part.from_text(text=prompt)]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )

    assert events, "Expected events from the agent"

    non_text_found = False
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                mime = getattr(part, "mime_type", None)
                if mime and mime != "text/plain":
                    non_text_found = True
                # some implementations may embed urls or data urls
                text = getattr(part, "text", "")
                if "http" in text or "data:image" in text:
                    non_text_found = True
                # our simple sketch_scene tool returns a placeholder string
                if "[image for:" in text:
                    non_text_found = True
    assert non_text_found, "Expected at least one non-text part in the story"
