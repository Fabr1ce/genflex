"""Central logging configuration for GenFlex.

Call setup_logging() once at startup. All loggers (including ADK internals)
will write to logs/app.log and stdout.
"""

import logging
import os
import sys
from pathlib import Path


def setup_logging() -> None:
    log_file = os.environ.get("LOG_FILE", "logs/app.log")
    if not log_file:
        return

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]

    # Root logger captures everything including ADK/google internals
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers, force=True)

    # ADK agent reasoning lives under these namespaces
    for name in ("google.adk", "google.genai", "app"):
        logging.getLogger(name).setLevel(logging.DEBUG)
