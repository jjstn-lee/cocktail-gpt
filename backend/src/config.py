"""Configuration for the cocktail recommendation agent."""

import os

LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5")
