"""User preference and constraint storage using JSON files."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from loguru import logger

from src.state import Preferences, Constraints


class UserStore:
    """Store and retrieve user preferences and constraints as JSON files."""

    def __init__(self, base_dir: str = "data/users"):
        """
        Initialize the UserStore.

        Args:
            base_dir: Directory to store user JSON files. Will be created if it doesn't exist.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("UserStore initialized", extra={"base_dir": str(self.base_dir)})

    def _sanitize_user_id(self, user_id: str) -> str:
        """
        Sanitize user_id to prevent path traversal.

        Replace any non-alphanumeric, non-dash, non-underscore characters with underscores.
        """
        return re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id)

    def _get_user_file(self, user_id: str) -> Path:
        """Get the JSON file path for a user."""
        sanitized = self._sanitize_user_id(user_id)
        return self.base_dir / f"{sanitized}.json"

    def _load_user_file(self, user_id: str) -> dict:
        """Load user file or return empty structure."""
        file_path = self._get_user_file(user_id)
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load user file", extra={"user_id": user_id, "error": str(e)})
                return self._empty_user_data()
        return self._empty_user_data()

    def _empty_user_data(self) -> dict:
        """Return empty user data structure."""
        return {
            "preferences": {
                "preferred_spirits": [],
                "genre_spirits": [],
                "preferred_flavors": [],
                "abv_preference": None,
                "style_preferences": [],
            },
            "constraints": {
                "allergies": [],
                "ingredients_on_hand": [],
                "max_abv": None,
            },
            "feedback": [],
            "recommendation_history": [],
            "session_count": 0,
            "updated_at": None,
        }

    def _save_user_file(self, user_id: str, data: dict) -> None:
        """Save user file."""
        file_path = self._get_user_file(user_id)
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info("User file saved", extra={"user_id": user_id, "file": str(file_path)})
        except IOError as e:
            logger.error("Failed to save user file", extra={"user_id": user_id, "error": str(e)})
            raise

    def get_preferences(self, user_id: str) -> Preferences | None:
        """
        Get user preferences.

        Returns Preferences model or None if not set.
        """
        data = self._load_user_file(user_id)
        prefs_dict = data.get("preferences", {})
        if prefs_dict and any(prefs_dict.values()):
            try:
                return Preferences(**prefs_dict)
            except Exception as e:
                logger.warning("Failed to parse preferences", extra={"user_id": user_id, "error": str(e)})
                return None
        return None

    def get_constraints(self, user_id: str) -> Constraints | None:
        """
        Get user constraints.

        Returns Constraints model or None if not set.
        """
        data = self._load_user_file(user_id)
        constraints_dict = data.get("constraints", {})
        if constraints_dict and any(constraints_dict.values()):
            try:
                return Constraints(**constraints_dict)
            except Exception as e:
                logger.warning("Failed to parse constraints", extra={"user_id": user_id, "error": str(e)})
                return None
        return None

    def save_preferences(self, user_id: str, prefs: Preferences) -> None:
        """
        Save user preferences.

        Merges with existing data (only updates preferences).
        """
        data = self._load_user_file(user_id)
        data["preferences"] = prefs.model_dump()
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_user_file(user_id, data)

    def save_constraints(self, user_id: str, constraints: Constraints) -> None:
        """
        Save user constraints.

        Merges with existing data (only updates constraints).
        """
        data = self._load_user_file(user_id)
        data["constraints"] = constraints.model_dump()
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_user_file(user_id, data)

    def clear(self, user_id: str) -> None:
        """
        Clear all user data.

        Deletes the user's JSON file.
        """
        file_path = self._get_user_file(user_id)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info("User data cleared", extra={"user_id": user_id})
            except IOError as e:
                logger.error("Failed to clear user data", extra={"user_id": user_id, "error": str(e)})
                raise

    def load_feedback(self, user_id: str) -> list[dict]:
        """
        Load all feedback entries for a user.

        Returns a list of feedback dicts with keys: cocktail_name, rating, session_id, timestamp.
        """
        data = self._load_user_file(user_id)
        feedback = data.get("feedback", [])
        logger.debug("Feedback loaded", extra={"user_id": user_id, "count": len(feedback)})
        return feedback

    def save_feedback(self, user_id: str, feedback_entry: dict) -> None:
        """
        Save a single feedback entry.

        Appends to the existing feedback list.
        feedback_entry should have: cocktail_name, rating, session_id, timestamp.
        """
        data = self._load_user_file(user_id)
        if "feedback" not in data:
            data["feedback"] = []
        data["feedback"].append(feedback_entry)
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_user_file(user_id, data)
        logger.debug("Feedback saved", extra={"user_id": user_id, "cocktail_name": feedback_entry.get("cocktail_name")})

    def load_recommendation_history(self, user_id: str) -> list[dict]:
        """
        Load recommendation history for a user.

        Returns a list of the last N sessions with their recommendations.
        """
        data = self._load_user_file(user_id)
        history = data.get("recommendation_history", [])
        logger.debug("Recommendation history loaded", extra={"user_id": user_id, "count": len(history)})
        return history

    def save_session_recommendations(self, user_id: str, session_id: str, cocktails: list[str]) -> None:
        """
        Save recommendations for a session.

        Appends a new session entry with cocktail names.
        cocktails should be a list of cocktail names (strings).
        """
        data = self._load_user_file(user_id)
        if "recommendation_history" not in data:
            data["recommendation_history"] = []
        session_entry = {
            "session_id": session_id,
            "cocktails": cocktails,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        data["recommendation_history"].append(session_entry)
        # Keep only last 10 sessions to avoid unbounded growth
        data["recommendation_history"] = data["recommendation_history"][-10:]
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_user_file(user_id, data)
        logger.debug("Session recommendations saved", extra={"user_id": user_id, "session_id": session_id, "count": len(cocktails)})

    def get_session_count(self, user_id: str) -> int:
        """Get the total number of completed recommendation sessions."""
        data = self._load_user_file(user_id)
        return data.get("session_count", 0)

    def increment_session_count(self, user_id: str) -> int:
        """Increment session count and return the new value."""
        data = self._load_user_file(user_id)
        count = data.get("session_count", 0)
        count += 1
        data["session_count"] = count
        data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_user_file(user_id, data)
        logger.debug("Session count incremented", extra={"user_id": user_id, "count": count})
        return count
