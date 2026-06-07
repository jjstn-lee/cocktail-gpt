"""Utilities for streaming graph execution with status updates."""

# Map node names to user-friendly status messages
NODE_STATUS_MESSAGES = {
    "supervisor": "🔍 Analyzing your intent...",
    "ingest": "📊 Gathering your data...",
    "profile_builder": "👤 Building your profile...",
    "preference_extractor": "❤️ Extracting your preferences...",
    "constraint_checker": "⚠️ Checking constraints...",
    "recommender": "🍹 Crafting cocktail recommendations...",
    "clarify": "❓ Preparing clarification...",
    "output": "✨ Finalizing response...",
    # Profile update path
    "profile_updater": "💾 Updating your profile...",
    # Other intents
    "rate_cocktail": "👍 Recording your feedback...",
    "explain_recommendation": "📖 Preparing explanation...",
    "manage_restrictions": "🚫 Applying restrictions...",
    "retrieve_profile": "👤 Retrieving your profile...",
    "conversational_fallback": "💬 Thinking...",
    "self_information": "ℹ️ Fetching capabilities...",
}


def get_status_message(node_name: str) -> str:
    """Get a user-friendly status message for a node."""
    return NODE_STATUS_MESSAGES.get(node_name, f"Processing {node_name}...")
