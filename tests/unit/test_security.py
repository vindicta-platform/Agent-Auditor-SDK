"""
Unit tests for SecureKeyManager.

Layer: Unit
Scope: Security utilities and key handling.
"""

import os
import pytest
import re
from agent_auditor.security import (
    SecureKeyManager, 
    APIKeyNotFoundError, 
    InvalidAPIKeyError, 
    SENSITIVE_PATTERNS
)


class TestSecureKeyManager:
    """Tests for secure API key handling per Constitution II."""

    def test_reads_key_from_environment(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "test-key-12345"
        
        # Act
        manager = SecureKeyManager()
        key = manager.get_key()
        
        # Assert
        assert key == "test-key-12345"

    def test_raises_without_env_var(self):
        # Arrange
        os.environ.pop("GEMINI_API_KEY", None)
        
        # Act & Assert
        with pytest.raises(APIKeyNotFoundError):
            manager = SecureKeyManager()
            manager.get_key()

    def test_key_never_in_str_repr(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "AIzaSyD_secret_key_12345"
        manager = SecureKeyManager()
        
        # Act
        str_repr = str(manager)
        repr_output = repr(manager)
        
        # Assert
        assert "AIzaSyD" not in str_repr
        assert "AIzaSyD" not in repr_output
        assert "secret" not in str_repr
        assert "secret" not in repr_output

    def test_key_masked_display(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "AIzaSyD_my_secret_key"
        manager = SecureKeyManager()
        
        # Act
        masked = manager.get_masked_key()
        
        # Assert
        # Should show something like "AI***...ey"
        assert masked.startswith("AI")
        assert masked.endswith("ey")
        assert "secret" not in masked
        assert len(masked) < len("AIzaSyD_my_secret_key")

    def test_sanitize_removes_key_from_string(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "secret_api_key_123"
        manager = SecureKeyManager()
        dirty = "Error occurred with key secret_api_key_123 in request"
        
        # Act
        clean = manager.sanitize(dirty)
        
        # Assert
        assert "secret_api_key_123" not in clean
        assert "[REDACTED]" in clean or "***" in clean

    def test_sanitize_error_creates_safe_exception(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "my_secret_key_value"
        manager = SecureKeyManager()
        original_error = Exception("Failed with key my_secret_key_value")
        
        # Act
        safe_error = manager.create_safe_error(original_error)
        
        # Assert
        assert "my_secret_key_value" not in str(safe_error)

    def test_validates_key_format(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = ""
        
        # Act & Assert
        with pytest.raises(InvalidAPIKeyError):
            manager = SecureKeyManager()
            manager.validate()

    def test_supports_alternative_env_var(self):
        # Arrange
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ["AISTUDIO__API_KEY"] = "alt_key_from_aistudio"
        
        # Act
        manager = SecureKeyManager()
        key = manager.get_key()
        
        # Assert
        assert key == "alt_key_from_aistudio"


class TestSecurityPatterns:
    """Test security patterns and constants."""

    def test_sensitive_patterns_defined(self):
        # Arrange & Act & Assert
        assert isinstance(SENSITIVE_PATTERNS, (list, tuple))
        assert len(SENSITIVE_PATTERNS) > 0

    def test_patterns_match_common_key_formats(self):
        # Arrange
        test_keys = [
            "AIzaSyD_test_key_123",
            "AIzaSyA_another_key",
        ]
        
        # Act & Assert
        for key in test_keys:
            matched = any(re.search(pattern, key) for pattern in SENSITIVE_PATTERNS)
            assert matched, f"Pattern should match {key}"
