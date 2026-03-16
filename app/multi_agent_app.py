# Multi-Agent Orchestrator - Coordinates all storytelling agents
# Copyright 2026 Google LLC

# The multi-agent pipeline is wired directly into root_agent in agent.py via sub_agents.
# This module re-exports app for backward compatibility.

from .agent import app

__all__ = ["app"]
