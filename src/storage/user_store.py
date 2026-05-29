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
                "preferred_flavors": [],
                "abv_preference": None,
                "style_preferences": [],
            },
            "constraints": {
                "allergies": [],
                "ingredients_on_hand": [],
                "max_abv": None,
            },
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
