"""Simple CLI for interacting with the GenFlex storyteller agent.

Usage:
    python run_agent.py

You can type prompts and see the agent's output streamed back.  This is
handy during hackathon development or local demos.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# load environment variables so credentials and settings are available
load_dotenv()

# Set global logging level to DEBUG
logging.basicConfig(level=logging.DEBUG)

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import google.auth.exceptions

from app.agent import root_agent
from app.app_utils.logging_config import setup_logging as _setup_logging


def setup_logging(log_file: str | None) -> None:
    if log_file is not None:
        os.environ["LOG_FILE"] = log_file
    _setup_logging()

def print_part(part) -> None:
    # helper to display an Event.Part in the console
    text = getattr(part, "text", None)
    mime = getattr(part, "mime_type", None)
    if mime and mime != "text/plain":
        msg = f"[{mime}] {text}"
        sys.stdout.write(msg + "\n")
        logging.info(msg)
    elif text:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        logging.info(text)
    # additional attributes such as ``image`` or ``url`` can be printed too
    url = getattr(part, "url", None)
    if url:
        msg = f"(url: {url})"
        sys.stdout.write(msg + "\n")
        logging.info(msg)


async def main(log_file: str | None = None) -> None:
    setup_logging(log_file)

    logging.info("Starting GenFlex storyteller CLI")

    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="cli", app_name="cli")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="cli")

    print("GenFlex storyteller CLI. Type a prompt or 'quit' to exit.")
    while True:
        try:
            prompt = input("> ")
        except EOFError:
            logging.info("CLI session ended by EOF")
            break
        if not prompt or prompt.strip().lower() in ("quit", "exit"):
            logging.info("CLI session ended by user")
            break

        logging.info(f"User prompt: {prompt}")

        message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

        try:
            async for event in runner.run_async(
                user_id="cli",
                session_id=session.id,
                new_message=message,
            ):
                # Log agent reasoning and actions
                if not getattr(event, "is_final_response", lambda: False)():
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                logging.debug(f"Agent Thought ({event.author}): {part.text.strip()}")
                    if event.actions:
                        for action in event.actions:
                            if isinstance(action, types.FunctionCall):
                                logging.debug(f"Agent Tool Call ({event.author}): {action.name}({action.args})")
                else: # This is the final response
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            print_part(part)
        except Exception as e:
            if (
                isinstance(e, google.auth.exceptions.TransportError)
                or isinstance(e, google.auth.exceptions.DefaultCredentialsError)
                or "oauth2.googleapis.com" in str(e)
            ):
                error_msg = (
                    "Authentication error: unable to reach Google OAuth endpoints.\n"
                    "Please run `gcloud auth login` (or set GOOGLE_APPLICATION_CREDENTIALS) and try again.\n"
                )
                sys.stderr.write(error_msg)
                logging.error(f"Authentication error: {e}")
                return
            logging.error(f"Unexpected error during agent run: {e}")
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the GenFlex storyteller CLI.")
    parser.add_argument(
        "--log-file",
        default=None,
        help=(
            "Optional log file path (relative or absolute). "
            "Defaults to `LOG_FILE` env var or `logs/run_agent.log` if unset. "
            "Pass an empty string to disable file logging."
        ),
    )
    args = parser.parse_args()

    env_log_file = os.getenv("LOG_FILE")
    log_file = args.log_file if args.log_file is not None else env_log_file

    asyncio.run(main(log_file))
