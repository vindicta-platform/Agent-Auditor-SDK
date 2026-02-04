"""
Secure API key management for Agent-Auditor-SDK.

This module implements Constitution Principle II: Security-First API Key Handling.

Rules:
1. API keys MUST only be read from environment variables
2. API keys MUST NEVER be logged, serialized, or exposed in error messages
3. API keys MUST be sanitized from all stack traces and debug output
4. No hardcoded keys, no config files containing secrets
"""

import os
import re
from typing import Optional


# Patterns that match common API key formats for sanitization
SENSITIVE_PATTERNS: tuple[str, ...] = (
    r"AIzaSy[a-zA-Z0-9_-]+",     # Google AI Studio format (variable length)
    r"sk-[a-zA-Z0-9]+",          # OpenAI format (for future)
    r"[a-zA-Z0-9_-]{20,}",       # Generic long alphanumeric (fuzzy)
)


class APIKeyNotFoundError(Exception):
    """Raised when no API key is found in environment."""
    pass


class InvalidAPIKeyError(Exception):
    """Raised when API key format is invalid."""
    pass


class SecureKeyManager:
    """
    Secure API key management with sanitization.
    
    Never exposes the actual key in str(), repr(), or error messages.
    Always read from environment variables only.
    
    Environment Variables (checked in order):
        - GEMINI_API_KEY (primary)
        - AISTUDIO__API_KEY (alternative)
    
    Example:
        manager = SecureKeyManager()
        key = manager.get_key()  # Returns actual key
        print(manager)  # Shows "[SecureKeyManager: AI***...ey]"
    """
    
    # Environment variables to check, in order
    ENV_VARS = ("GEMINI_API_KEY", "AISTUDIO__API_KEY")
    
    def __init__(self) -> None:
        """Initialize the key manager. Does not read key until needed."""
        self._cached_key: Optional[str] = None
    
    def get_key(self) -> str:
        """
        Get the API key from environment.
        
        Returns:
            The API key string.
            
        Raises:
            APIKeyNotFoundError: If no key is found in environment.
        """
        if self._cached_key is not None:
            return self._cached_key
        
        for env_var in self.ENV_VARS:
            key = os.environ.get(env_var)
            if key is not None:  # Allow empty string through so validate() can check it
                self._cached_key = key
                return key
        
        raise APIKeyNotFoundError(
            "No API key found. Set GEMINI_API_KEY or AISTUDIO__API_KEY environment variable."
        )
    
    def validate(self) -> None:
        """
        Validate the API key format.
        
        Raises:
            InvalidAPIKeyError: If the key is empty or obviously invalid.
        """
        key = self.get_key()
        
        if not key or len(key.strip()) == 0:
            raise InvalidAPIKeyError("API key is empty")
        
        if len(key) < 10:
            raise InvalidAPIKeyError("API key is too short")
    
    def get_masked_key(self) -> str:
        """
        Get a masked version of the key for display.
        
        Returns:
            Key with middle characters replaced, e.g., "AI***...ey"
        """
        try:
            key = self.get_key()
            if len(key) <= 4:
                return "***"
            return f"{key[:2]}***...{key[-2:]}"
        except APIKeyNotFoundError:
            return "[NO KEY]"
    
    def sanitize(self, text: str) -> str:
        """
        Remove the API key from a string.
        
        Args:
            text: String that may contain the API key.
            
        Returns:
            String with API key replaced by [REDACTED].
        """
        try:
            key = self.get_key()
            if key in text:
                text = text.replace(key, "[REDACTED]")
        except APIKeyNotFoundError:
            pass
        
        return text
    
    def create_safe_error(self, error: Exception) -> Exception:
        """
        Create a sanitized version of an exception.
        
        Args:
            error: Original exception that may contain API key.
            
        Returns:
            New exception with API key removed from message.
        """
        sanitized_message = self.sanitize(str(error))
        return type(error)(sanitized_message)
    
    def __str__(self) -> str:
        """Return safe string representation."""
        return f"[SecureKeyManager: {self.get_masked_key()}]"
    
    def __repr__(self) -> str:
        """Return safe repr without exposing key."""
        return f"SecureKeyManager(masked={self.get_masked_key()!r})"
