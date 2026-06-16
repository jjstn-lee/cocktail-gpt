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


def apply_hard_filters(
    cocktails: list[dict[str, Any]],
    constraints: Any,  # Constraints Pydantic model, or None
) -> list[dict[str, Any]]:
    """
    Apply safety-critical exclusions: allergy ingredients and max ABV.

    Shared by recommender, browse_by_attribute, and filter_cocktails so allergy/ABV
    semantics stay in lockstep across the agent's KB-querying paths.
    """
    if constraints is None:
        return list(cocktails)

    allergies = [a.lower() for a in (constraints.allergies or [])]
    max_abv = constraints.max_abv

    survivors = []
    for cocktail in cocktails:
        if allergies:
            ingredients_items = [
                ing.get("item", "").lower() for ing in (cocktail.get("ingredients") or [])
            ]
            all_ingredients_text = " ".join(ingredients_items)
            if any(allergy in all_ingredients_text for allergy in allergies):
                continue
        if max_abv is not None and cocktail.get("abv_estimate", 0) > max_abv:
            continue
        survivors.append(cocktail)
    return survivors


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
    ingredients_on_hand = [i.lower() for i in (constraints.ingredients_on_hand or [])]
    preferred_spirits = [s.lower() for s in (preferences.preferred_spirits or [])]
    preferred_flavors = [f.lower() for f in (preferences.preferred_flavors or [])]
    abv_preference = preferences.abv_preference

    abv_tier_map = {
        "light": "low",
        "moderate": "medium",
        "strong": "high",
    }
    target_abv_tier = abv_tier_map.get(abv_preference.lower(), None) if abv_preference else None

    survivors = apply_hard_filters(cocktails, constraints)
    scored = []

    for cocktail in survivors:
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


def filter_by_attribute(
    cocktails: list[dict[str, Any]],
    attribute_query: str,
    constraints: Any,  # Constraints Pydantic model, or None
) -> list[dict[str, Any]]:
    """
    Return up to 10 cocktails from the KB that match a free-form attribute query.

    Applies hard constraint exclusions first, then scores each cocktail by how
    strongly the attribute_query matches its spirit_category, flavor_notes,
    mood/occasion/season/style tags, ingredients, or non-alcoholic flag.

    Args:
        cocktails: All cocktails from load_cocktails()
        attribute_query: Free-form string from the user (e.g., "smoky", "gin", "summer")
        constraints: Optional Constraints — allergies/max_abv exclusions applied first

    Returns:
        Up to 10 cocktails with score > 0, sorted descending by score.
        If nothing matches scoring, returns the first 10 hard-filter survivors as
        a fallback so the LLM still has KB-grounded candidates to pick from.
    """
    query = (attribute_query or "").lower().strip()
    survivors = apply_hard_filters(cocktails, constraints)

    if not query:
        return survivors[:10]

    scored: list[tuple[dict[str, Any], int]] = []
    for cocktail in survivors:
        score = 0
        spirit_category = (cocktail.get("spirit_category") or "").lower()
        if query in spirit_category:
            score += 3

        flavor_notes = [str(f).lower() for f in (cocktail.get("flavor_notes") or [])]
        if any(query in note for note in flavor_notes):
            score += 2

        tag_fields = ("mood_tags", "occasion_tags", "season_tags", "style_tags")
        tags = [
            str(t).lower()
            for field in tag_fields
            for t in (cocktail.get(field) or [])
        ]
        if any(query in tag for tag in tags):
            score += 2

        ingredient_items = [
            (ing.get("item") or "").lower() for ing in (cocktail.get("ingredients") or [])
        ]
        if any(query in item for item in ingredient_items):
            score += 1

        if query in ("non-alcoholic", "nonalcoholic", "alcohol-free", "mocktail") and cocktail.get(
            "is_non_alcoholic"
        ):
            score += 3

        if score > 0:
            scored.append((cocktail, score))

    if not scored:
        logger.debug(
            "filter_by_attribute: no scored matches; returning hard-filter survivors as fallback",
            extra={"query": query, "survivors": len(survivors)},
        )
        return survivors[:10]

    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:10]]


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
