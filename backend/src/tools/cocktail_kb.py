"""Cocktail knowledgebase loader, filter, and formatter for the recommender node."""

import json
import os
from pathlib import Path
from typing import Any
from loguru import logger

# Module-level cache for cocktails (loaded once at import)
_COCKTAIL_CACHE: list[dict[str, Any]] | None = None
_KB_DIR = Path(__file__).parent.parent.parent / "data" / "cocktails"


def load_cocktails() -> list[dict[str, Any]]:
    """
    Load all cocktail JSON files from the knowledgebase directory.
    Results are cached at module level.

    Raises RuntimeError if the directory does not exist or all files fail to parse.
    """
    global _COCKTAIL_CACHE

    if _COCKTAIL_CACHE is not None:
        return _COCKTAIL_CACHE

    if not _KB_DIR.exists():
        raise RuntimeError(f"Cocktail knowledgebase directory not found: {_KB_DIR}")

    cocktails = []
    failed_files = []

    for json_file in sorted(_KB_DIR.glob("*.json")):
        try:
            with open(json_file, "r") as f:
                cocktail = json.load(f)
            cocktails.append(cocktail)
        except (json.JSONDecodeError, KeyError) as e:
            failed_files.append((json_file.name, str(e)))
            logger.warning(f"Failed to parse cocktail file {json_file.name}: {e}")

    if not cocktails:
        raise RuntimeError(
            f"No valid cocktail files found in {_KB_DIR}. "
            f"Failed to parse: {', '.join(name for name, _ in failed_files)}"
        )

    if failed_files:
        logger.warning(
            f"Loaded {len(cocktails)} cocktails with {len(failed_files)} parse failures"
        )

    _COCKTAIL_CACHE = cocktails
    return cocktails


def filter_cocktails(
    cocktails: list[dict[str, Any]],
    preferences: Any,  # Preferences Pydantic model
    constraints: Any,  # Constraints Pydantic model
) -> list[dict[str, Any]]:
    """
    Filter and score cocktails based on user preferences and constraints.

    Hard exclusions applied first (remove cocktails that don't match):
    1. Allergies: exclude if any ingredient item contains allergy token (substring match)
    2. Max ABV: exclude if abv_estimate exceeds constraint

    Soft scoring (higher score = better match):
    - +2: spirit_category matches preferred_spirits
    - +1: preferred_spirits appears in ingredient items
    - +1: ingredients_on_hand appears in ingredient items
    - +1: preferred_flavors appears in flavor_notes
    - +1: abv_tier matches mapped abv_preference

    Args:
        cocktails: List of cocktail dicts from load_cocktails()
        preferences: Preferences model with preferred_spirits, preferred_flavors, abv_preference
        constraints: Constraints model with allergies, ingredients_on_hand, max_abv

    Returns:
        Top 20 cocktails by score, or all survivors if fewer than 5 pass hard filters.
    """
    # Prepare filter parameters
    allergies = [a.lower() for a in (constraints.allergies or [])]
    ingredients_on_hand = [i.lower() for i in (constraints.ingredients_on_hand or [])]
    max_abv = constraints.max_abv
    preferred_spirits = [s.lower() for s in (preferences.preferred_spirits or [])]
    preferred_flavors = [f.lower() for f in (preferences.preferred_flavors or [])]
    abv_preference = preferences.abv_preference

    # Map ABV preference to tier
    abv_tier_map = {
        "light": "low",
        "moderate": "medium",
        "strong": "high",
    }
    target_abv_tier = abv_tier_map.get(abv_preference.lower(), None) if abv_preference else None

    # Apply hard filters and soft scoring
    scored = []

    for cocktail in cocktails:
        # Hard exclusion 1: allergies
        if allergies:
            ingredients_items = [ing["item"].lower() for ing in (cocktail.get("ingredients") or [])]
            all_ingredients_text = " ".join(ingredients_items)
            if any(allergy in all_ingredients_text for allergy in allergies):
                continue  # Skip this cocktail

        # Hard exclusion 2: max ABV
        if max_abv is not None:
            abv = cocktail.get("abv_estimate", 0)
            if abv > max_abv:
                continue  # Skip this cocktail

        # Soft scoring
        score = 0

        # Spirit preference scoring
        spirit_category = cocktail.get("spirit_category", "").lower()
        if preferred_spirits:
            if spirit_category in preferred_spirits:
                score += 2
            # Also check ingredient items for secondary spirits
            ingredients_items = [ing["item"].lower() for ing in (cocktail.get("ingredients") or [])]
            for spirit in preferred_spirits:
                if any(spirit in item for item in ingredients_items):
                    score += 1

        # Ingredients on hand scoring
        if ingredients_on_hand:
            ingredients_items = [ing["item"].lower() for ing in (cocktail.get("ingredients") or [])]
            for hand_item in ingredients_on_hand:
                if any(hand_item in item for item in ingredients_items):
                    score += 1

        # Flavor preference scoring
        if preferred_flavors:
            flavor_notes = [f.lower() for f in (cocktail.get("flavor_notes") or [])]
            for flavor in preferred_flavors:
                if flavor in flavor_notes:
                    score += 1

        # ABV tier preference scoring
        if target_abv_tier:
            cocktail_tier = cocktail.get("abv_tier", "").lower()
            if cocktail_tier == target_abv_tier:
                score += 1

        scored.append((cocktail, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Return top 20, or all survivors if fewer than 5
    if len(scored) < 5:
        logger.warning(f"cocktail_kb: only {len(scored)} cocktails passed hard filters (expected 5+)")
        return [c for c, _ in scored]

    return [c for c, _ in scored[:20]]


def format_for_prompt(cocktails: list[dict[str, Any]]) -> str:
    """
    Format a list of cocktails into a compact, prompt-friendly text block.

    Each cocktail is rendered as a numbered entry with name, spirit, method, ABV tier,
    flavor notes, and occasion tags on one or two lines.

    Args:
        cocktails: List of cocktail dicts (pre-filtered by filter_cocktails)

    Returns:
        A formatted string suitable for inclusion in an LLM prompt.
    """
    lines = []
    for i, cocktail in enumerate(cocktails, start=1):
        name = cocktail.get("name", "Unknown")
        spirit = cocktail.get("spirit_category", "mixed").title()
        method = cocktail.get("method", "stirred")
        abv_tier = cocktail.get("abv_tier", "medium").capitalize()
        flavor_notes = ", ".join(cocktail.get("flavor_notes", [])[:3])
        occasion_tags = ", ".join(cocktail.get("occasion_tags", [])[:2])

        line = f"{i}. {name} ({spirit.lower()}, {method}, {abv_tier}-ABV)"
        if flavor_notes:
            line += f" — {flavor_notes}"
        if occasion_tags:
            line += f" — {occasion_tags}"

        lines.append(line)

    return "\n".join(lines)
