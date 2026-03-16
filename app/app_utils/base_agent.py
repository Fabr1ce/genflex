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

import datetime
import logging
import os
from typing import Any

from google.adk.agents import Agent
from app.app_utils.token_tracker import get_token_tracker

class TokenTrackingAgent(Agent):
    """Custom agent that tracks token usage and logs agent activity."""

    async def run_async(self, *args, **kwargs):
        """Override run_async to track token usage and log activity."""
        logging.info(f"--- AGENT WORK START: {self.name} ---")
        # Get token tracker instance (avoid circular imports)
        token_tracker = get_token_tracker()

        # Store input for token tracking
        input_message = kwargs.get('new_message', '')
        input_text = self._extract_text_from_message(input_message)
        model_name = self.model.model if hasattr(self.model, 'model') else 'unknown'

        # Call the parent implementation and yield all events
        async for event in super().run_async(*args, **kwargs):
            yield event

        # After all events are yielded, do token tracking
        try:
            # Estimate tokens (rough approximation: ~4 characters per token)
            estimated_input_tokens = len(input_text) // 4 if input_text else 0
            # For output, we don't have access to the final result, so we'll use a rough estimate
            estimated_output_tokens = 100  # Rough estimate
            total_tokens = estimated_input_tokens + estimated_output_tokens

            # Log the token usage
            token_tracker.log_token_usage(
                tokens_used=total_tokens,
                model=model_name,
                operation=f"{self.name}_execution",
                metadata={
                    "input_length": len(input_text) if input_text else 0,
                    "estimated_input_tokens": estimated_input_tokens,
                    "estimated_output_tokens": estimated_output_tokens,
                    "agent": self.name,
                    "timestamp": datetime.datetime.now().isoformat()
                }
            )
            logging.info(f"--- AGENT WORK COMPLETE: {self.name} ---")

        except Exception as e:
            # Don't fail the operation if token tracking fails
            logging.warning(f"Failed to track token usage for {self.name}: {e}")

    def _extract_text_from_message(self, message: Any) -> str:
        """Extract text content from a message object."""
        if hasattr(message, 'parts'):
            text_parts = []
            for part in message.parts:
                if hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
            return ' '.join(text_parts)
        return str(message)
